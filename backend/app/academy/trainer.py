from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

from sqlalchemy import text

from app.academy.synthetic import SyntheticTrainer
from app.db import SessionLocal
from app.schema import ensure_schema

logger = logging.getLogger(__name__)


class BatchTrainer:
    """Orchestrates synthetic training for multiple agents."""

    def __init__(self) -> None:
        self.synthetic_trainer = SyntheticTrainer()

    async def train_all_agents(self, *, conversations_per_agent: int = 100, batch_size: int = 5, wait_s: int = 60) -> list[dict[str, Any]]:
        conversations_per_agent = max(1, min(500, int(conversations_per_agent)))
        batch_size = max(1, min(12, int(batch_size)))
        wait_s = max(0, min(300, int(wait_s)))

        with SessionLocal() as db:
            ensure_schema(db.get_bind())
            agents = (
                db.execute(
                    text(
                        """
                        select code as agent_code, coalesce(human_name, name) as human_name, name as role
                        from agent_catalog
                        where status = 'active'
                        order by code;
                        """
                    )
                )
                .mappings()
                .all()
            )

        logger.info("Starting batch training for %s agents", len(agents))
        logger.info("Config: %s conversations/agent, batch=%s, wait=%ss", conversations_per_agent, batch_size, wait_s)

        all_results: list[dict[str, Any]] = []
        total_batches = (len(agents) + batch_size - 1) // batch_size
        started = time.time()

        for i in range(0, len(agents), batch_size):
            batch = agents[i : i + batch_size]
            batch_num = i // batch_size + 1
            logger.info("=== BATCH %s/%s ===", batch_num, total_batches)
            logger.info("Agents: %s", ", ".join(a["agent_code"] for a in batch))

            tasks = [
                self.synthetic_trainer.train_agent(
                    agent_code=a["agent_code"],
                    conversation_count=conversations_per_agent,
                )
                for a in batch
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            for a, r in zip(batch, results):
                if isinstance(r, Exception):
                    logger.error("❌ Failed: %s - %s", a["agent_code"], r)
                else:
                    all_results.append(r)
                    logger.info(
                        "✅ Completed: %s (%s) - avg=%.1f (high=%s, low=%s)",
                        r.get("human_name") or a["human_name"],
                        a["agent_code"],
                        float(r.get("avg_quality_score") or 0),
                        r.get("high_scores"),
                        r.get("low_scores"),
                    )

            if (i + batch_size) < len(agents) and wait_s:
                logger.info("Waiting %ss before next batch...", wait_s)
                await asyncio.sleep(wait_s)

        logger.info("Batch training complete in %.1f minutes", (time.time() - started) / 60.0)
        return all_results

    async def get_training_summary(self) -> dict[str, Any]:
        with SessionLocal() as db:
            ensure_schema(db.get_bind())
            rows = (
                db.execute(
                    text(
                        """
                        select
                          ac.code as agent_code,
                          coalesce(ac.human_name, ac.name) as human_name,
                          ac.name as role,
                          ts.avg_quality_score,
                          ts.total_interactions,
                          ts.completed_at
                        from agent_catalog ac
                        join training_sessions ts on ts.agent_code = ac.code
                        where ts.session_type = 'synthetic'
                          and ts.status = 'completed'
                        order by ts.avg_quality_score desc nulls last;
                        """
                    )
                )
                .mappings()
                .all()
            )

        if not rows:
            return {"total_agents": 0, "avg_quality_overall": 0, "agents": []}

        scores = [float(r.get("avg_quality_score") or 0) for r in rows if r.get("avg_quality_score") is not None]
        avg_quality = (sum(scores) / len(scores)) if scores else 0.0
        out_rows: list[dict[str, Any]] = []
        for r in rows:
            d = dict(r)
            if hasattr(d.get("completed_at"), "isoformat"):
                d["completed_at"] = d["completed_at"].isoformat()
            out_rows.append(d)

        return {"total_agents": len(rows), "avg_quality_overall": round(avg_quality, 2), "agents": out_rows}
