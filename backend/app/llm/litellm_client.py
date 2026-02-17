from __future__ import annotations

import time
import uuid
from typing import Any

from app.settings import settings


class LLMError(RuntimeError):
    pass


def to_litellm_model(provider: str, model: str) -> str:
    provider = (provider or "").strip()
    model = (model or "").strip()
    if not provider or not model:
        raise LLMError("Agent LLM provider/model is not configured.")

    # Allow storing full litellm model identifiers in DB (e.g. anthropic/claude-...).
    if "/" in model:
        return model
    return f"{provider}/{model}"


def execute_via_litellm(
    *,
    provider: str,
    model: str,
    system: str,
    user: str,
    trace_id: str | None = None,
) -> dict[str, Any]:
    trace_id = trace_id or str(uuid.uuid4())
    model_used = to_litellm_model(provider, model)

    if settings.llm_mock:
        start = time.perf_counter()
        reply = f"[MOCK:{model_used}] {user}"
        latency_ms = int((time.perf_counter() - start) * 1000)
        return {
            "trace_id": trace_id,
            "model_used": model_used,
            "latency_ms": latency_ms,
            "response": reply,
        }

    try:
        from litellm import completion  # type: ignore[import-not-found]
    except Exception as e:  # pragma: no cover
        raise LLMError("litellm is not installed. Run: pip install -r requirements.txt") from e

    start = time.perf_counter()
    try:
        resp = completion(
            model=model_used,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            metadata={"trace_id": trace_id},
        )
    except Exception as e:
        msg = str(e).strip()
        if msg:
            msg = msg.replace("\n", " ")
            if len(msg) > 240:
                msg = msg[:240] + "..."
            raise LLMError(f"LLM call failed: {e.__class__.__name__}: {msg}") from e
        raise LLMError(f"LLM call failed: {e.__class__.__name__}") from e

    latency_ms = int((time.perf_counter() - start) * 1000)
    text = ""
    if isinstance(resp, dict):
        try:
            text = resp["choices"][0]["message"]["content"]
        except Exception:
            text = ""

    return {
        "trace_id": trace_id,
        "model_used": model_used,
        "latency_ms": latency_ms,
        "response": text,
        "raw": resp,
    }
