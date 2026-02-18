from __future__ import annotations

import json
import logging
import os
from typing import Any

import anyio

from app.llm.litellm_client import LLMError, execute_via_litellm

logger = logging.getLogger(__name__)


def _extract_json_object(text: str) -> dict[str, Any]:
    t = (text or "").strip()
    if not t:
        raise json.JSONDecodeError("empty", t, 0)

    # Strip fenced code blocks if present.
    if t.startswith("```"):
        parts = t.split("```")
        if len(parts) >= 2:
            # parts[1] may start with a language tag line.
            candidate = parts[1].strip()
            if "\n" in candidate and candidate.split("\n", 1)[0].strip().isalpha():
                candidate = candidate.split("\n", 1)[1].strip()
            t = candidate

    # Fast path: direct JSON.
    try:
        obj = json.loads(t)
        if isinstance(obj, dict):
            return obj
    except json.JSONDecodeError:
        pass

    # Fallback: extract first {...} block.
    start = t.find("{")
    end = t.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise json.JSONDecodeError("no object", t, 0)

    obj = json.loads(t[start : end + 1])
    if not isinstance(obj, dict):
        raise json.JSONDecodeError("not dict", t, 0)
    return obj


class ResponseEvaluator:
    """Evaluates agent response quality using an LLM-as-judge."""

    EVALUATION_CRITERIA: dict[str, dict[str, Any]] = {
        "helpfulness": {"description": "Does the response answer the user's question and provide value?", "weight": 0.30},
        "accuracy": {"description": "Is the information correct and appropriate for the context?", "weight": 0.30},
        "professionalism": {"description": "Is the tone appropriate, polite, and professional?", "weight": 0.20},
        "completeness": {"description": "Does the response address all aspects of the inquiry?", "weight": 0.10},
        "clarity": {"description": "Is the response easy to understand and well-structured?", "weight": 0.10},
    }

    def __init__(self) -> None:
        # Default judge model: Claude Sonnet 4.5 (as requested).
        self.provider = os.getenv("ACADEMY_JUDGE_PROVIDER", "anthropic").strip() or "anthropic"
        self.model = os.getenv("ACADEMY_JUDGE_MODEL", "claude-sonnet-4-5-20250929").strip() or "claude-sonnet-4-5-20250929"

    async def evaluate(
        self,
        *,
        user_message: str,
        agent_response: str,
        agent_role: str,
        expected_qualities: list[str] | None = None,
    ) -> dict[str, Any]:
        """
        Evaluate a single response across multiple criteria.

        Returns:
        {
          "overall": 75.5,
          "subscores": { "helpfulness": 80, ... }
        }
        """
        subscores = await self._judge_all(
            user_message=user_message,
            agent_response=agent_response,
            agent_role=agent_role,
            expected_qualities=expected_qualities or [],
        )

        overall = 0.0
        for criterion, details in self.EVALUATION_CRITERIA.items():
            overall += float(subscores.get(criterion, 50.0)) * float(details["weight"])

        return {"overall": round(overall, 2), "subscores": subscores}

    async def _judge_all(
        self,
        *,
        user_message: str,
        agent_response: str,
        agent_role: str,
        expected_qualities: list[str],
    ) -> dict[str, float]:
        judge_system = (
            "You are an expert evaluator grading an AI agent response.\n"
            "Score each criterion as a number from 0 to 100.\n"
            "Return ONLY valid JSON with keys: helpfulness, accuracy, professionalism, completeness, clarity.\n"
            "Output must start with '{' and end with '}'. No markdown, no commentary."
        )

        qualities_text = f"Expected qualities: {', '.join(expected_qualities)}" if expected_qualities else "Expected qualities: (none provided)"
        criteria_lines = "\n".join(
            f"- {k}: {v['description']}" for k, v in self.EVALUATION_CRITERIA.items()
        )

        judge_user = f"""Evaluate a {agent_role}'s response to a user.

Scoring rubric (0-100):
- 0-30: Poor (fails criterion significantly)
- 31-60: Adequate (meets criterion partially)
- 61-85: Good (meets criterion well)
- 86-100: Excellent (exceeds criterion)

Criteria:
{criteria_lines}

{qualities_text}

User Message:
{user_message}

Agent Response:
{agent_response}

Return JSON only, example:
{{"helpfulness": 80, "accuracy": 85, "professionalism": 70, "completeness": 65, "clarity": 75}}
"""

        try:
            result = await anyio.to_thread.run_sync(
                lambda: execute_via_litellm(
                    provider=self.provider,
                    model=self.model,
                    system=judge_system,
                    user=judge_user,
                )
            )
            text = (result.get("response") or result.get("content") or result.get("text") or "").strip()
            data = _extract_json_object(text)
        except (LLMError, json.JSONDecodeError) as e:
            snippet = ""
            try:
                snippet = (text or "")[:240].replace("\n", " ")
            except Exception:
                snippet = "<unavailable>"
            logger.error("Judge evaluation failed: %s | response_snippet=%r", e, snippet)
            return {k: 50.0 for k in self.EVALUATION_CRITERIA.keys()}
        except Exception as e:  # pragma: no cover
            logger.exception("Unexpected evaluator error: %s", e)
            return {k: 50.0 for k in self.EVALUATION_CRITERIA.keys()}

        subscores: dict[str, float] = {}
        for k in self.EVALUATION_CRITERIA.keys():
            try:
                v = float(data.get(k, 50.0))
            except Exception:
                v = 50.0
            subscores[k] = max(0.0, min(100.0, v))
        return subscores
