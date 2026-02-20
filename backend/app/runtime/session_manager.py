from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import uuid

from sqlalchemy import text

from app.db import SessionLocal
from app.settings import settings


@dataclass
class SessionSnapshot:
    session_id: str
    org_id: str
    agent_code: str
    summary: str
    turns_count: int
    compacted_turns: int
    recent_messages: list[dict[str, str]]


class SessionManager:
    """Session lifecycle + memory compaction manager."""

    def ensure_session(self, *, org_id: str, agent_code: str, session_id: str | None) -> str:
        sid = (session_id or "").strip() or f"sess-{uuid.uuid4()}"
        with SessionLocal() as db:
            agent_row = db.execute(
                text("select code from agent_catalog where lower(code) = lower(:agent_code) limit 1;"),
                {"agent_code": agent_code},
            ).mappings().first()
            if not agent_row:
                raise RuntimeError(f"Unknown agent_code: {agent_code}")
            canonical_agent_code = str(agent_row["code"])
            active_count = db.execute(
                text(
                    """
                    select count(*)::int
                    from chat_sessions
                    where org_id = :org_id and status = 'active';
                    """
                ),
                {"org_id": org_id},
            ).scalar_one()
            if int(active_count or 0) >= int(settings.session_max_parallel_per_org):
                raise RuntimeError("Org active session limit reached")
            db.execute(
                text("insert into organizations (org_id, name) values (:org_id, :name) on conflict (org_id) do nothing"),
                {"org_id": org_id, "name": ""},
            )
            db.execute(
                text(
                    """
                    insert into chat_sessions
                      (session_id, org_id, agent_code, status, title, metadata, created_at, updated_at, last_activity_at)
                    values
                      (:session_id, :org_id, :agent_code, 'active', '', '{}'::jsonb, now(), now(), now())
                    on conflict (session_id)
                    do update set
                      org_id = excluded.org_id,
                      agent_code = excluded.agent_code,
                      updated_at = now(),
                      last_activity_at = now();
                    """
                ),
                {"session_id": sid, "org_id": org_id, "agent_code": canonical_agent_code},
            )
            db.commit()
        return sid

    def append_message(
        self,
        *,
        org_id: str,
        session_id: str,
        agent_code: str,
        role: str,
        content: str,
        metadata: dict | None = None,
    ) -> None:
        with SessionLocal() as db:
            db.execute(
                text(
                    """
                    insert into chat_session_messages (session_id, role, content, metadata, created_at)
                    values (:session_id, :role, :content, cast(:metadata as jsonb), now());
                    """
                ),
                {
                    "session_id": session_id,
                    "role": role,
                    "content": content or "",
                    "metadata": "{}" if not metadata else __import__("json").dumps(metadata),
                },
            )
            inc = 1 if role == "assistant" else 0
            db.execute(
                text(
                    """
                    update chat_sessions
                    set turns_count = turns_count + :inc,
                        updated_at = now(),
                        last_activity_at = now()
                    where session_id = :session_id and org_id = :org_id and agent_code = :agent_code;
                    """
                ),
                {"session_id": session_id, "org_id": org_id, "agent_code": agent_code, "inc": inc},
            )
            db.commit()

        self.compact_if_needed(org_id=org_id, session_id=session_id, agent_code=agent_code)

    def get_snapshot(self, *, org_id: str, session_id: str, agent_code: str) -> SessionSnapshot:
        recent_turns = max(1, int(settings.session_context_recent_turns))
        with SessionLocal() as db:
            row = db.execute(
                text(
                    """
                    select session_id, org_id, agent_code, summary, turns_count, compacted_turns
                    from chat_sessions
                    where session_id = :session_id and org_id = :org_id and agent_code = :agent_code
                    limit 1;
                    """
                ),
                {"session_id": session_id, "org_id": org_id, "agent_code": agent_code},
            ).mappings().first()
            if not row:
                return SessionSnapshot(
                    session_id=session_id,
                    org_id=org_id,
                    agent_code=agent_code,
                    summary="",
                    turns_count=0,
                    compacted_turns=0,
                    recent_messages=[],
                )

            # Pull approx 2 messages per turn.
            msgs = db.execute(
                text(
                    """
                    select role, content
                    from chat_session_messages
                    where session_id = :session_id
                    order by created_at desc
                    limit :limit;
                    """
                ),
                {"session_id": session_id, "limit": recent_turns * 2},
            ).mappings().all()
            messages = list(reversed([{"role": str(m["role"]), "content": str(m["content"])} for m in msgs]))

            return SessionSnapshot(
                session_id=str(row["session_id"]),
                org_id=str(row["org_id"]),
                agent_code=str(row["agent_code"]),
                summary=str(row["summary"] or ""),
                turns_count=int(row["turns_count"] or 0),
                compacted_turns=int(row["compacted_turns"] or 0),
                recent_messages=messages,
            )

    def render_context_block(self, *, org_id: str, session_id: str, agent_code: str) -> str:
        snap = self.get_snapshot(org_id=org_id, session_id=session_id, agent_code=agent_code)
        lines: list[str] = []
        if snap.summary:
            lines.append("Session summary from earlier conversation:")
            lines.append(snap.summary)
        if snap.recent_messages:
            lines.append("Most recent messages in this session:")
            for msg in snap.recent_messages:
                role = "User" if msg["role"] == "user" else "Assistant"
                lines.append(f"{role}: {msg['content']}")
        return "\n".join(lines)

    def delete_session(self, *, org_id: str, session_id: str) -> bool:
        with SessionLocal() as db:
            deleted = db.execute(
                text("delete from chat_sessions where session_id = :session_id and org_id = :org_id;"),
                {"session_id": session_id, "org_id": org_id},
            ).rowcount
            db.commit()
            return bool(deleted)

    def list_sessions(self, *, org_id: str, limit: int = 100) -> list[dict]:
        cap = max(1, min(int(limit), 500))
        with SessionLocal() as db:
            rows = db.execute(
                text(
                    """
                    select session_id, agent_code, status, title, turns_count, compacted_turns, created_at, updated_at, last_activity_at
                    from chat_sessions
                    where org_id = :org_id
                    order by last_activity_at desc
                    limit :limit;
                    """
                ),
                {"org_id": org_id, "limit": cap},
            ).mappings().all()
            return [dict(r) for r in rows]

    def compact_if_needed(self, *, org_id: str, session_id: str, agent_code: str) -> None:
        if not settings.session_compaction_enabled:
            return
        threshold = max(6, int(settings.session_compaction_turns))
        keep_recent_turns = max(4, int(settings.session_context_recent_turns))
        keep_recent_messages = keep_recent_turns * 2

        with SessionLocal() as db:
            row = db.execute(
                text(
                    """
                    select turns_count, summary
                    from chat_sessions
                    where session_id = :session_id and org_id = :org_id and agent_code = :agent_code
                    limit 1;
                    """
                ),
                {"session_id": session_id, "org_id": org_id, "agent_code": agent_code},
            ).mappings().first()
            if not row:
                return
            turns = int(row["turns_count"] or 0)
            if turns <= threshold:
                return

            # Pull old message set (excluding newest keep_recent_messages) to summarize.
            old_msgs = db.execute(
                text(
                    """
                    with ordered as (
                      select id, role, content, created_at,
                             row_number() over(order by created_at desc) as rn
                      from chat_session_messages
                      where session_id = :session_id
                    )
                    select id, role, content
                    from ordered
                    where rn > :keep_recent
                    order by rn desc;
                    """
                ),
                {"session_id": session_id, "keep_recent": keep_recent_messages},
            ).mappings().all()
            if not old_msgs:
                return

            # Deterministic compaction summary (no extra LLM cost).
            summary_lines = ["Compacted session summary:"]
            for message in old_msgs[:30]:
                role = "User" if str(message["role"]) == "user" else "Assistant"
                content = str(message["content"] or "").strip().replace("\n", " ")
                if len(content) > 180:
                    content = content[:180].rstrip() + "..."
                if content:
                    summary_lines.append(f"- {role}: {content}")
            new_summary = "\n".join(summary_lines)
            prev_summary = str(row["summary"] or "").strip()
            if prev_summary:
                combined = prev_summary + "\n\n" + new_summary
                # Keep bounded size.
                new_summary = combined[-7000:]

            old_count = len(old_msgs)
            db.execute(
                text(
                    """
                    with ordered as (
                      select id, row_number() over(order by created_at desc) as rn
                      from chat_session_messages
                      where session_id = :session_id
                    )
                    delete from chat_session_messages csm
                    using ordered
                    where csm.id = ordered.id
                      and ordered.rn > :keep_recent;
                    """
                ),
                {"session_id": session_id, "keep_recent": keep_recent_messages},
            )
            # Compact old turns to keep turns_count bounded.
            compacted_now = max(1, old_count // 2)
            db.execute(
                text(
                    """
                    update chat_sessions
                    set summary = :summary,
                        compacted_turns = compacted_turns + :compacted_now,
                        turns_count = greatest(0, turns_count - :compacted_now),
                        updated_at = now()
                    where session_id = :session_id and org_id = :org_id and agent_code = :agent_code;
                    """
                ),
                {
                    "summary": new_summary,
                    "compacted_now": compacted_now,
                    "session_id": session_id,
                    "org_id": org_id,
                    "agent_code": agent_code,
                },
            )
            db.commit()


session_manager = SessionManager()
