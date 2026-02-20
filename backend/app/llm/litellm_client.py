from __future__ import annotations

import logging
import time
import uuid
from typing import Any

from app.llm.search_detector import search_detector
from app.runtime.model_policy import model_policy_service
from app.runtime.tool_registry import ToolCallContext, tool_registry
from app.settings import settings

logger = logging.getLogger(__name__)


class LLMError(RuntimeError):
    pass


def _is_retryable_error(exc: Exception) -> bool:
    name = exc.__class__.__name__.lower()
    msg = str(exc).lower()
    retry_markers = (
        "timeout",
        "timed out",
        "temporarily unavailable",
        "service unavailable",
        "rate limit",
        "connection reset",
        "connection aborted",
        "bad gateway",
        "gateway timeout",
    )
    return ("timeout" in name) or any(marker in msg for marker in retry_markers)


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
    enable_search: bool = True,
    enable_docs: bool = True,
    org_id: str | None = None,
    session_id: str | None = None,
    agent_code: str | None = None,
) -> dict[str, Any]:
    trace_id = trace_id or str(uuid.uuid4())
    search_used = False
    docs_used = False
    user_message = user
    additional_blocks: list[str] = []

    runtime_context = ToolCallContext(
        org_id=(org_id or "org_test"),
        session_id=session_id,
        agent_code=agent_code,
    )

    if enable_search and settings.enable_web_search:
        try:
            if search_detector.needs_search(user):
                query = search_detector.extract_search_query(user)
                call = tool_registry.run(
                    tool_name="web_search",
                    context=runtime_context,
                    args={"query": query, "num_results": 5},
                )
                if call.get("ok"):
                    formatted = (((call.get("data") or {}).get("formatted")) or "").strip()
                    if formatted:
                        additional_blocks.append(
                            "[CURRENT WEB INFORMATION]\n"
                            f"Search query: {query}\n"
                            f"{formatted}\n"
                            "[END WEB INFORMATION]"
                        )
                        search_used = True
        except Exception as e:
            logger.error("Web search integration failed: %s", e)

    if enable_docs and settings.enable_document_retrieval:
        try:
            from app.tools.document_search import doc_search

            if doc_search.needs_docs(user):
                call = tool_registry.run(
                    tool_name="document_search",
                    context=runtime_context,
                    args={"query": user, "limit": 3},
                )
                if call.get("ok"):
                    formatted_docs = (((call.get("data") or {}).get("formatted")) or "").strip()
                    if formatted_docs and "No relevant internal documents found." not in formatted_docs:
                        additional_blocks.append(
                            "[COMPANY KNOWLEDGE BASE]\n"
                            f"{formatted_docs}\n"
                            "[END KNOWLEDGE BASE]"
                        )
                        docs_used = True
        except Exception as e:
            logger.error("Document retrieval integration failed: %s", e)

    if additional_blocks:
        user_message = (
            f"{user}\n\n" + "\n\n".join(additional_blocks) + "\n\n"
            "Use available context blocks above to provide accurate answers. "
            "If context is missing, clearly state assumptions."
        )

    if org_id:
        preference = model_policy_service.get_preference(org_id=org_id, agent_code=agent_code)
        if preference:
            pref_provider = (preference.get("preferred_provider") or "").strip()
            pref_model = (preference.get("preferred_model") or "").strip()
            if pref_provider:
                provider = pref_provider
            if pref_model:
                model = pref_model

    # Smart multi-LLM routing path (with cache + cost tracking).
    if getattr(settings, "multi_llm_router_enabled", False):
        try:
            from app.llm.multi_router import LLMRequest, get_multi_llm_router

            routed = get_multi_llm_router().execute(
                LLMRequest(
                    system=system,
                    user=user_message,
                    trace_id=trace_id,
                    preferred_provider=(provider or None),
                    preferred_model=(model or None),
                )
            )
            return {
                "trace_id": routed.get("trace_id") or trace_id,
                "model_used": routed.get("model_used") or "",
                "latency_ms": int(routed.get("latency_ms") or 0),
                "response": routed.get("response") or "",
                "tokens_used": int(routed.get("tokens_used") or 0),
                "raw": routed.get("raw") or {},
                "cached": bool(routed.get("cached")),
                "route_level": routed.get("route_level"),
                "complexity_score": routed.get("complexity_score"),
                "search_used": search_used,
                "docs_used": docs_used,
            }
        except Exception as e:
            # If request relies entirely on router (no explicit provider/model), surface router failure directly.
            if not provider or not model:
                raise LLMError(f"Smart router execution failed: {e}") from e
            # Otherwise fall back to legacy direct LiteLLM path.
            pass

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
            "search_used": search_used,
            "docs_used": docs_used,
        }

    try:
        from litellm import completion  # type: ignore[import-not-found]
    except Exception as e:  # pragma: no cover
        raise LLMError("litellm is not installed. Run: pip install -r requirements.txt") from e

    start = time.perf_counter()
    retries = max(0, int(settings.litellm_retries))
    resp: Any = None
    last_error: Exception | None = None
    for attempt in range(retries + 1):
        try:
            resp = completion(
                model=model_used,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user_message},
                ],
                metadata={"trace_id": trace_id},
                timeout=max(5, int(settings.litellm_timeout_s)),
            )
            last_error = None
            break
        except Exception as e:
            last_error = e
            if attempt >= retries or not _is_retryable_error(e):
                break
            time.sleep(min(1.5, 0.35 * (attempt + 1)))

    if last_error is not None:
        msg = str(last_error).strip()
        if msg:
            msg = msg.replace("\n", " ")
            if len(msg) > 240:
                msg = msg[:240] + "..."
            raise LLMError(f"LLM call failed: {last_error.__class__.__name__}: {msg}") from last_error
        raise LLMError(f"LLM call failed: {last_error.__class__.__name__}") from last_error

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
        if not text:
            # Some providers expose content in delta or chunks.
            text = _coerce_text(choice0.get("delta"))
    except Exception:
        text = ""

    if not text:
        raise LLMError("LLM returned an empty response.")

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
        "search_used": search_used,
        "docs_used": docs_used,
    }
    if org_id:
        preference = model_policy_service.get_preference(org_id=org_id, agent_code=agent_code)
        if preference:
            pref_provider = (preference.get("preferred_provider") or "").strip()
            pref_model = (preference.get("preferred_model") or "").strip()
            if pref_provider:
                provider = pref_provider
            if pref_model:
                model = pref_model
