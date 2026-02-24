from __future__ import annotations

import json
import logging
import os
import re
import uuid
from typing import Any

from app.llm.multi_router import LLMRequest, get_multi_llm_router
from app.settings import settings

logger = logging.getLogger(__name__)


class MemoryExtractor:
    """Extract durable memory items from prior conversation messages."""

    _ALLOWED_TYPES = {"preference", "org_fact", "instruction", "context"}

    async def extract_from_messages(self, *, messages: list[dict[str, str]], agent_code: str | None = None) -> list[dict[str, Any]]:
        if not messages:
            return []
        extracted = await self._extract_via_llm(messages=messages, agent_code=agent_code)
        if extracted:
            return extracted
        return self._extract_heuristic(messages)

    async def _extract_via_llm(self, *, messages: list[dict[str, str]], agent_code: str | None) -> list[dict[str, Any]]:
        if not self._llm_available():
            return []
        conversation = []
        for message in messages[-24:]:
            role = str(message.get("role") or "").strip()
            content = str(message.get("content") or "").strip()
            if role and content:
                conversation.append(f"{role.upper()}: {content}")
        if not conversation:
            return []

        prompt = (
            "Extract durable memories from the conversation. "
            "Only include facts likely useful in future chats.\n"
            "Return strict JSON array of objects with keys:\n"
            "memory_type (preference|org_fact|instruction|context), memory_key, memory_value, confidence(0-1).\n"
            "If nothing durable exists, return [].\n\n"
            f"Agent: {agent_code or 'unknown'}\n"
            "Conversation:\n"
            + "\n".join(conversation)
        )
        try:
            provider = settings.academy_judge_provider or "groq"
            model = settings.academy_judge_model or "llama-3.3-70b-versatile"
            result = await get_multi_llm_router().execute(
                LLMRequest(
                    system="You extract structured memory for assistant systems. Output JSON only.",
                    user=prompt,
                    trace_id=str(uuid.uuid4()),
                    preferred_provider=provider,
                    preferred_model=model,
                )
            )
            raw = str(result.get("response") or "").strip()
            if not raw:
                return []
            parsed = json.loads(self._extract_json(raw))
            if not isinstance(parsed, list):
                return []
            return self._normalize(parsed)
        except Exception as exc:
            logger.warning("Memory extractor LLM fallback to heuristic: %s", exc)
            return []

    def _llm_available(self) -> bool:
        keys = ("GROQ_API_KEY", "ANTHROPIC_API_KEY", "OPENAI_API_KEY", "GEMINI_API_KEY")
        return any(bool(os.getenv(key)) for key in keys)

    def _extract_json(self, text: str) -> str:
        text = text.strip()
        if text.startswith("["):
            return text
        match = re.search(r"\[[\s\S]*\]", text)
        if match:
            return match.group(0)
        return "[]"

    def _normalize(self, items: list[Any]) -> list[dict[str, Any]]:
        normalized: list[dict[str, Any]] = []
        for item in items:
            if not isinstance(item, dict):
                continue
            memory_type = str(item.get("memory_type") or "context").strip().lower()
            if memory_type not in self._ALLOWED_TYPES:
                memory_type = "context"
            memory_key = str(item.get("memory_key") or "").strip()[:128]
            memory_value = str(item.get("memory_value") or "").strip()[:8000]
            if not memory_key or not memory_value:
                continue
            try:
                confidence = float(item.get("confidence") if item.get("confidence") is not None else 0.7)
            except Exception:
                confidence = 0.7
            normalized.append(
                {
                    "memory_type": memory_type,
                    "memory_key": memory_key,
                    "memory_value": memory_value,
                    "confidence": max(0.0, min(1.0, confidence)),
                }
            )
        return normalized

    def _extract_heuristic(self, messages: list[dict[str, str]]) -> list[dict[str, Any]]:
        user_text = " ".join(str(m.get("content") or "") for m in messages if (m.get("role") or "").lower() == "user")
        output: list[dict[str, Any]] = []
        
        # Tone/Format existing heuristics
        tone_match = re.search(r"\b(casual|formal|friendly|professional)\b", user_text, re.IGNORECASE)
        if tone_match:
            output.append({"memory_type": "preference", "memory_key": "tone", "memory_value": tone_match.group(1).lower(), "confidence": 0.62})
        format_match = re.search(r"\b(markdown|json|email|csv|bullet points?)\b", user_text, re.IGNORECASE)
        if format_match:
            output.append({"memory_type": "instruction", "memory_key": "output_format", "memory_value": format_match.group(1).lower(), "confidence": 0.58})

        # Lead Intake heuristics (Jessica special)
        name_match = re.search(r"(?:my name is|i am|this is)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)", user_text, re.IGNORECASE)
        if name_match:
            output.append({"memory_type": "context", "memory_key": "user_name", "memory_value": name_match.group(1).strip(), "confidence": 0.85})
        
        company_match = re.search(r"(?:work at|from|with)\s+([A-Z][a-zA-Z0-9]+(?:\s+[A-Z][a-zA-Z0-9]+)?)", user_text)
        if company_match:
            output.append({"memory_type": "org_fact", "memory_key": "user_company", "memory_value": company_match.group(1).strip(), "confidence": 0.80})

        return output


memory_extractor = MemoryExtractor()
