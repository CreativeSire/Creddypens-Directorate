from __future__ import annotations

import time
import uuid
from typing import Any

from app.settings import settings


class LLMError(RuntimeError):
    pass


def _coerce_text(value: Any) -> str:
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, list):
        parts: list[str] = []
        for item in value:
            text = _coerce_text(item)
            if text:
                parts.append(text)
        return "\n".join(parts).strip()
    if isinstance(value, dict):
        for key in ("text", "content", "value"):
            text = _coerce_text(value.get(key))
            if text:
                return text
    return ""


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
            "tokens_used": max(1, len(user.split()) * 2),
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

    # LiteLLM returns a dict-like pydantic model (ModelResponse) for many providers.
    # Normalize to a plain dict so content extraction is consistent.
    data: Any = resp
    if not isinstance(data, dict):
        if hasattr(data, "model_dump"):
            data = data.model_dump()
        elif hasattr(data, "dict"):
            data = data.dict()
        elif hasattr(data, "to_dict"):
            data = data.to_dict()
        else:
            try:
                data = dict(data)  # type: ignore[arg-type]
            except Exception:
                data = {}

    text = ""
    try:
        choice0 = (data.get("choices") or [None])[0] or {}
        msg = choice0.get("message") or {}
        text = _coerce_text(msg.get("content"))
        if not text:
            # Some providers return `text` directly on choice.
            text = _coerce_text(choice0.get("text"))
        if not text:
            # Responses API style fallback
            text = _coerce_text(data.get("output_text"))
    except Exception:
        text = ""

    if getattr(settings, "litellm_debug", False):
        print("=" * 80)
        print("LITELLM DEBUG:")
        try:
            print(f"Raw response type: {type(resp)}")
            print(f"Raw response: {resp}")
        except Exception:
            print("Raw response: <unprintable>")
        print(f"Extracted text: {text!r}")
        print(f"Returning: {{'response': {text!r}}}")
        print("=" * 80)

    return {
        "trace_id": trace_id,
        "model_used": model_used,
        "latency_ms": latency_ms,
        "response": text,
        "tokens_used": int((data.get("usage") or {}).get("total_tokens") or 0),
        "raw": data,
    }
