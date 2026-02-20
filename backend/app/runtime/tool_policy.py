from __future__ import annotations

from sqlalchemy import text

from app.db import SessionLocal


class ToolPolicyService:
    DEFAULTS: dict[str, bool] = {
        "web_search": True,
        "document_search": True,
        "crm_action": False,
    }

    def is_allowed(self, *, org_id: str, tool_name: str, agent_code: str | None = None) -> bool:
        # Agent-specific override first, then org-level policy, then defaults.
        with SessionLocal() as db:
            if agent_code:
                row = db.execute(
                    text(
                        """
                        select allow
                        from org_tool_policies
                        where org_id = :org_id and agent_code = :agent_code and tool_name = :tool_name
                        limit 1;
                        """
                    ),
                    {"org_id": org_id, "agent_code": agent_code, "tool_name": tool_name},
                ).mappings().first()
                if row is not None:
                    return bool(row["allow"])

            row = db.execute(
                text(
                    """
                    select allow
                    from org_tool_policies
                    where org_id = :org_id and agent_code is null and tool_name = :tool_name
                    limit 1;
                    """
                ),
                {"org_id": org_id, "tool_name": tool_name},
            ).mappings().first()
            if row is not None:
                return bool(row["allow"])

        return bool(self.DEFAULTS.get(tool_name, False))

    def upsert_policy(
        self,
        *,
        org_id: str,
        tool_name: str,
        allow: bool,
        agent_code: str | None = None,
        config: dict | None = None,
    ) -> None:
        payload = __import__("json").dumps(config or {})
        with SessionLocal() as db:
            if agent_code is None:
                updated = db.execute(
                    text(
                        """
                        update org_tool_policies
                        set allow = :allow,
                            config = cast(:config as jsonb),
                            updated_at = now()
                        where org_id = :org_id
                          and tool_name = :tool_name
                          and agent_code is null;
                        """
                    ),
                    {
                        "org_id": org_id,
                        "tool_name": tool_name,
                        "allow": bool(allow),
                        "config": payload,
                    },
                ).rowcount
            else:
                updated = db.execute(
                    text(
                        """
                        update org_tool_policies
                        set allow = :allow,
                            config = cast(:config as jsonb),
                            updated_at = now()
                        where org_id = :org_id
                          and tool_name = :tool_name
                          and agent_code = :agent_code;
                        """
                    ),
                    {
                        "org_id": org_id,
                        "agent_code": agent_code,
                        "tool_name": tool_name,
                        "allow": bool(allow),
                        "config": payload,
                    },
                ).rowcount
            if not updated:
                db.execute(
                    text(
                        """
                        insert into org_tool_policies (org_id, agent_code, tool_name, allow, config, created_at, updated_at)
                        values (:org_id, :agent_code, :tool_name, :allow, cast(:config as jsonb), now(), now());
                        """
                    ),
                    {
                        "org_id": org_id,
                        "agent_code": agent_code,
                        "tool_name": tool_name,
                        "allow": bool(allow),
                        "config": payload,
                    },
                )
            db.commit()

    def list_policies(self, *, org_id: str) -> list[dict]:
        with SessionLocal() as db:
            rows = db.execute(
                text(
                    """
                    select org_id, agent_code, tool_name, allow, config, created_at, updated_at
                    from org_tool_policies
                    where org_id = :org_id
                    order by coalesce(agent_code, ''), tool_name;
                    """
                ),
                {"org_id": org_id},
            ).mappings().all()
            return [dict(r) for r in rows]


tool_policy_service = ToolPolicyService()
