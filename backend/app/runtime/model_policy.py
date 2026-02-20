from __future__ import annotations

import json

from sqlalchemy import text

from app.db import SessionLocal


class ModelPolicyService:
    """BYOK/org model preference policy store."""

    def get_preference(self, *, org_id: str, agent_code: str | None = None) -> dict | None:
        with SessionLocal() as db:
            if agent_code:
                row = db.execute(
                    text(
                        """
                        select preferred_provider, preferred_model, reasoning_effort, metadata
                        from org_model_policies
                        where org_id = :org_id and agent_code = :agent_code
                        limit 1;
                        """
                    ),
                    {"org_id": org_id, "agent_code": agent_code},
                ).mappings().first()
                if row:
                    return dict(row)
            row = db.execute(
                text(
                    """
                    select preferred_provider, preferred_model, reasoning_effort, metadata
                    from org_model_policies
                    where org_id = :org_id and agent_code is null
                    limit 1;
                    """
                ),
                {"org_id": org_id},
            ).mappings().first()
            return dict(row) if row else None

    def upsert_preference(
        self,
        *,
        org_id: str,
        preferred_provider: str | None,
        preferred_model: str | None,
        reasoning_effort: str | None = None,
        agent_code: str | None = None,
        metadata: dict | None = None,
    ) -> None:
        payload = json.dumps(metadata or {})
        with SessionLocal() as db:
            if agent_code is None:
                updated = db.execute(
                    text(
                        """
                        update org_model_policies
                        set preferred_provider = :preferred_provider,
                            preferred_model = :preferred_model,
                            reasoning_effort = :reasoning_effort,
                            metadata = cast(:metadata as jsonb),
                            updated_at = now()
                        where org_id = :org_id
                          and agent_code is null;
                        """
                    ),
                    {
                        "org_id": org_id,
                        "preferred_provider": preferred_provider,
                        "preferred_model": preferred_model,
                        "reasoning_effort": reasoning_effort,
                        "metadata": payload,
                    },
                ).rowcount
            else:
                updated = db.execute(
                    text(
                        """
                        update org_model_policies
                        set preferred_provider = :preferred_provider,
                            preferred_model = :preferred_model,
                            reasoning_effort = :reasoning_effort,
                            metadata = cast(:metadata as jsonb),
                            updated_at = now()
                        where org_id = :org_id
                          and agent_code = :agent_code;
                        """
                    ),
                    {
                        "org_id": org_id,
                        "agent_code": agent_code,
                        "preferred_provider": preferred_provider,
                        "preferred_model": preferred_model,
                        "reasoning_effort": reasoning_effort,
                        "metadata": payload,
                    },
                ).rowcount
            if not updated:
                db.execute(
                    text(
                        """
                        insert into org_model_policies
                          (org_id, agent_code, preferred_provider, preferred_model, reasoning_effort, metadata, created_at, updated_at)
                        values
                          (:org_id, :agent_code, :preferred_provider, :preferred_model, :reasoning_effort, cast(:metadata as jsonb), now(), now());
                        """
                    ),
                    {
                        "org_id": org_id,
                        "agent_code": agent_code,
                        "preferred_provider": preferred_provider,
                        "preferred_model": preferred_model,
                        "reasoning_effort": reasoning_effort,
                        "metadata": payload,
                    },
                )
            db.commit()

    def list_preferences(self, *, org_id: str) -> list[dict]:
        with SessionLocal() as db:
            rows = db.execute(
                text(
                    """
                    select org_id, agent_code, preferred_provider, preferred_model, reasoning_effort, metadata, created_at, updated_at
                    from org_model_policies
                    where org_id = :org_id
                    order by coalesce(agent_code, ''), updated_at desc;
                    """
                ),
                {"org_id": org_id},
            ).mappings().all()
            return [dict(r) for r in rows]


model_policy_service = ModelPolicyService()
