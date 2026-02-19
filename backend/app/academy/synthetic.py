from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import anyio
from sqlalchemy import select, text

from app.academy.evaluator import ResponseEvaluator
from app.db import SessionLocal
from app.llm.litellm_client import LLMError, execute_via_litellm
from app.models import AgentCatalog
from app.schema import ensure_schema

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class TrainingResult:
    session_id: str
    agent_code: str
    human_name: str | None
    conversations: int
    avg_quality_score: float
    high_scores: int
    low_scores: int


class SyntheticTrainer:
    """Runs synthetic training conversations for agents and stores evaluation results."""

    def __init__(self) -> None:
        self.evaluator = ResponseEvaluator()

    async def train_agent(
        self,
        *,
        agent_code: str,
        conversation_count: int = 100,
    ) -> dict[str, Any]:
        return await anyio.to_thread.run_sync(
            lambda: self._train_agent_sync(agent_code=agent_code, conversation_count=conversation_count)
        )

    def _train_agent_sync(self, *, agent_code: str, conversation_count: int) -> dict[str, Any]:
        conversation_count = max(1, min(500, int(conversation_count)))
        started = time.time()

        with SessionLocal() as db:
            ensure_schema(db.get_bind())

            agent = db.execute(select(AgentCatalog).where(AgentCatalog.code == agent_code)).scalars().first()
            if not agent:
                raise ValueError(f"Agent {agent_code} not found")

            # Pull scenarios for this agent. Prefer random ordering when available.
            scenarios = (
                db.execute(
                    text(
                        """
                        select id, user_message, expected_qualities
                        from test_scenarios
                        where agent_code = :agent_code and is_active = true
                        order by random()
                        limit :limit;
                        """
                    ),
                    {"agent_code": agent_code, "limit": conversation_count},
                )
                .mappings()
                .all()
            )

            if not scenarios:
                raise ValueError(f"No active scenarios found for {agent_code}")

            if len(scenarios) < conversation_count:
                logger.warning(
                    "Only %s scenarios available for %s (requested %s)",
                    len(scenarios),
                    agent_code,
                    conversation_count,
                )

            # Create training session.
            session_row = db.execute(
                text(
                    """
                    insert into training_sessions (agent_code, session_type, total_interactions)
                    values (:agent_code, 'synthetic', :total_interactions)
                    returning id;
                    """
                ),
                {"agent_code": agent_code, "total_interactions": int(len(scenarios))},
            ).mappings().first()
            if not session_row or not session_row.get("id"):
                raise RuntimeError("Failed to create training session")
            session_id = str(session_row["id"])
            db.commit()

            total_quality = 0.0
            high_scores = 0
            low_scores = 0
            completed = 0

            try:
                for idx, s in enumerate(scenarios, start=1):
                    user_message = (s.get("user_message") or "").strip()
                    expected_qualities = list(s.get("expected_qualities") or [])

                    if not user_message:
                        continue

                    try:
                        system = (agent.system_prompt or "").strip() or f"You are {agent.name}."
                        agent_llm = execute_via_litellm(
                            provider=agent.llm_provider or "",
                            model=agent.llm_model or "",
                            system=system,
                            user=user_message,
                        )
                        response_text = (agent_llm.get("response") or "").strip()
                        if not response_text:
                            raise LLMError("Agent returned an empty response.")

                        evaluation = self.evaluator.evaluate_sync(
                            user_message=user_message,
                            agent_response=response_text,
                            agent_role=agent.name or agent.code,
                            expected_qualities=expected_qualities,
                        )
                        quality_score = float(evaluation.get("overall") or 0.0)
                        subscores = evaluation.get("subscores") or {}

                        db.execute(
                            text(
                                """
                                insert into evaluation_results (
                                  training_session_id,
                                  scenario_id,
                                  agent_code,
                                  user_message,
                                  agent_response,
                                  quality_score,
                                  subscores,
                                  evaluated_at
                                )
                                values (
                                  :training_session_id,
                                  :scenario_id,
                                  :agent_code,
                                  :user_message,
                                  :agent_response,
                                  :quality_score,
                                  cast(:subscores as jsonb),
                                  :evaluated_at
                                );
                                """
                            ),
                            {
                                "training_session_id": session_id,
                                "scenario_id": str(s["id"]),
                                "agent_code": agent_code,
                                "user_message": user_message,
                                "agent_response": response_text,
                                "quality_score": quality_score,
                                "subscores": json.dumps(subscores),
                                "evaluated_at": datetime.now(timezone.utc),
                            },
                        )
                        db.commit()

                        total_quality += quality_score
                        completed += 1
                        if quality_score >= 85:
                            high_scores += 1
                        elif quality_score < 60:
                            low_scores += 1

                        if idx % 10 == 0:
                            avg_so_far = total_quality / max(1, completed)
                            logger.info(
                                "Synthetic training %s: %s/%s complete (avg %.1f)",
                                agent_code,
                                idx,
                                len(scenarios),
                                avg_so_far,
                            )
                    except Exception as e:
                        logger.error("Error in scenario %s/%s for %s: %s", idx, len(scenarios), agent_code, e)
                        db.rollback()
                        continue

                avg_quality = total_quality / completed if completed else 0.0

                db.execute(
                    text(
                        """
                        update training_sessions
                        set completed_at = now(),
                            avg_quality_score = :avg_quality,
                            status = 'completed'
                        where id = :id;
                        """
                    ),
                    {"avg_quality": float(avg_quality), "id": session_id},
                )
                db.commit()

                logger.info(
                    "Training complete for %s: avg=%.1f, high=%s, low=%s, conversations=%s, elapsed=%.1fs",
                    agent_code,
                    avg_quality,
                    high_scores,
                    low_scores,
                    completed,
                    time.time() - started,
                )

                return TrainingResult(
                    session_id=session_id,
                    agent_code=agent_code,
                    human_name=agent.human_name,
                    conversations=completed,
                    avg_quality_score=round(avg_quality, 2),
                    high_scores=high_scores,
                    low_scores=low_scores,
                ).__dict__
            except Exception as e:
                db.rollback()
                db.execute(
                    text(
                        """
                        update training_sessions
                        set completed_at = now(),
                            status = 'failed',
                            error_message = :msg
                        where id = :id;
                        """
                    ),
                    {"msg": str(e)[:500], "id": session_id},
                )
                db.commit()
                raise
