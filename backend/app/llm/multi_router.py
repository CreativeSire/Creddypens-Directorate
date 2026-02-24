from __future__ import annotations

import hashlib
import threading
import time
import uuid
from dataclasses import dataclass
from typing import Any

from app.settings import settings


class MultiLLMError(RuntimeError):
    pass


@dataclass(frozen=True)
class LLMRequest:
    system: str
    user: str
    trace_id: str
    preferred_provider: str | None = None
    preferred_model: str | None = None
    route_hint: str | None = None


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


def _normalize_model(provider: str, model: str) -> str:
    provider = (provider or "").strip()
    model = (model or "").strip()
    if not provider or not model:
        raise MultiLLMError("Provider/model required")
    if "/" in model:
        return model
    return f"{provider}/{model}"


def _extract_response(data: Any) -> tuple[str, int]:
    text = ""
    try:
        choice0 = (data.get("choices") or [None])[0] or {}
        msg = choice0.get("message") or {}
        text = _coerce_text(msg.get("content"))
        if not text:
            text = _coerce_text(choice0.get("text"))
        if not text:
            text = _coerce_text(data.get("output_text"))
        if not text:
            text = _coerce_text(choice0.get("delta"))
    except Exception:
        text = ""
    if not text:
        raise MultiLLMError("LLM returned an empty response.")
    return text, int((data.get("usage") or {}).get("total_tokens") or 0)


class BaseProvider:
    provider_name: str

    def __init__(self, provider_name: str, default_model: str):
        self.provider_name = provider_name
        self.default_model = default_model

    async def execute(self, *, model: str | None, system: str, user: str, trace_id: str) -> dict[str, Any]:
        model_used = _normalize_model(self.provider_name, (model or self.default_model))
        if settings.llm_mock:
            start = time.perf_counter()
            content = f"[MOCK:{model_used}] {user}"
            return {
                "trace_id": trace_id,
                "model_used": model_used,
                "latency_ms": int((time.perf_counter() - start) * 1000),
                "response": content,
                "tokens_used": max(1, len((system + " " + user).split()) * 2),
                "raw": {},
            }

        try:
            from litellm import acompletion  # type: ignore[import-not-found]
        except Exception as e:  # pragma: no cover
            raise MultiLLMError("litellm is not installed. Run: pip install -r requirements.txt") from e

        start = time.perf_counter()
        retries = max(0, int(settings.litellm_retries))
        resp: Any = None
        last_error: Exception | None = None
        
        import asyncio
        for attempt in range(retries + 1):
            try:
                resp = await acompletion(
                    model=model_used,
                    messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
                    metadata={"trace_id": trace_id},
                    timeout=max(5, int(settings.litellm_timeout_s)),
                )
                last_error = None
                break
            except Exception as e:
                last_error = e
                if attempt >= retries or not _is_retryable_error(e):
                    break
                # Non-blocking sleep
                await asyncio.sleep(min(1.5, 0.35 * (attempt + 1)))

        if last_error is not None:
            msg = str(last_error).strip()
            if msg:
                msg = msg.replace("\n", " ")
                if len(msg) > 260:
                    msg = msg[:260] + "..."
                raise MultiLLMError(f"LLM call failed: {last_error.__class__.__name__}: {msg}") from last_error
            raise MultiLLMError(f"LLM call failed: {last_error.__class__.__name__}") from last_error

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

        content, tokens = _extract_response(data)
        return {
            "trace_id": trace_id,
            "model_used": model_used,
            "latency_ms": int((time.perf_counter() - start) * 1000),
            "response": content,
            "tokens_used": tokens,
            "raw": data,
        }


class AnthropicProvider(BaseProvider):
    def __init__(self) -> None:
        super().__init__("anthropic", settings.anthropic_sonnet_model or "claude-sonnet-4-5-20250929")


class GeminiProvider(BaseProvider):
    def __init__(self) -> None:
        super().__init__("google", settings.gemini_pro_model or "gemini-2.5-pro")


class OpenAIProvider(BaseProvider):
    def __init__(self) -> None:
        super().__init__("openai", "gpt-4.1-mini")


class OllamaProvider(BaseProvider):
    def __init__(self) -> None:
        super().__init__("ollama", "llama3.1:8b")


class GroqProvider(BaseProvider):
    def __init__(self) -> None:
        super().__init__("groq", "llama-3.3-70b-versatile")


class ComplexityAnalyzer:
    COMPLEX_KEYWORDS = (
        "strategy",
        "architecture",
        "legal",
        "medical",
        "diagnose",
        "financial",
        "optimize",
        "tradeoff",
        "multi-step",
        "root cause",
    )
    MEDIUM_KEYWORDS = ("analyze", "compare", "summarize", "plan", "evaluate", "design")

    def score(self, text: str) -> tuple[str, float]:
        t = (text or "").lower()
        words = len(t.split())
        score = 0.0
        if words > 200:
            score += 0.45
        elif words > 80:
            score += 0.25
        else:
            score += 0.08

        complex_hits = sum(1 for k in self.COMPLEX_KEYWORDS if k in t)
        medium_hits = sum(1 for k in self.MEDIUM_KEYWORDS if k in t)
        score += min(0.50, complex_hits * 0.14)
        score += min(0.36, medium_hits * 0.12)
        score = min(1.0, score)

        if score >= 0.50:
            return "complex", score
        if score >= 0.24:
            return "medium", score
        return "simple", score


class ResponseCache:
    def __init__(self, ttl_s: int = 3600, max_items: int = 2000) -> None:
        self.ttl_s = max(1, int(ttl_s))
        self.max_items = max(100, int(max_items))
        self._lock = threading.Lock()
        self._items: dict[str, tuple[float, dict[str, Any]]] = {}

    def _prune(self, now: float) -> None:
        expired = [k for k, (exp, _) in self._items.items() if exp <= now]
        for k in expired:
            self._items.pop(k, None)
        if len(self._items) > self.max_items:
            for k in list(self._items.keys())[: len(self._items) - self.max_items]:
                self._items.pop(k, None)

    def make_key(self, *, provider: str, model: str, system: str, user: str) -> str:
        payload = f"{provider}|{model}|{system}|{user}".encode("utf-8")
        return hashlib.sha256(payload).hexdigest()

    def get(self, key: str) -> dict[str, Any] | None:
        now = time.time()
        with self._lock:
            self._prune(now)
            row = self._items.get(key)
            if not row:
                return None
            exp, value = row
            if exp <= now:
                self._items.pop(key, None)
                return None
            return dict(value)

    def put(self, key: str, value: dict[str, Any]) -> None:
        now = time.time()
        with self._lock:
            self._prune(now)
            self._items[key] = (now + self.ttl_s, dict(value))


class CostTracker:
    COST_PER_1K_TOKENS_USD = {
        "anthropic/claude-opus-4-5-20251101": 0.0300,
        "anthropic/claude-sonnet-4-5-20250929": 0.0060,
        "openai/gpt-4.1-mini": 0.0010,
        "google/gemini-2.5-pro": 0.0020,
        "groq/llama-3.3-70b-versatile": 0.0006,
        "ollama/llama3.1:8b": 0.0001,
    }

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.total_calls = 0
        self.cache_hits = 0
        self.actual_cost_usd = 0.0
        self.baseline_cost_usd = 0.0
        self.baseline_model = "anthropic/claude-opus-4-5-20251101"

    def _model_cost(self, model_used: str) -> float:
        return float(self.COST_PER_1K_TOKENS_USD.get(model_used, 0.004))

    def track(self, *, model_used: str, tokens: int, cache_hit: bool) -> None:
        tokens = max(0, int(tokens))
        actual = 0.0 if cache_hit else (tokens / 1000.0) * self._model_cost(model_used)
        baseline = (tokens / 1000.0) * self._model_cost(self.baseline_model)
        with self._lock:
            self.total_calls += 1
            if cache_hit:
                self.cache_hits += 1
            self.actual_cost_usd += actual
            self.baseline_cost_usd += baseline

    def summary(self) -> dict[str, Any]:
        with self._lock:
            savings = max(0.0, self.baseline_cost_usd - self.actual_cost_usd)
            reduction = (savings / self.baseline_cost_usd * 100.0) if self.baseline_cost_usd > 0 else 0.0
            return {
                "total_calls": self.total_calls,
                "cache_hits": self.cache_hits,
                "cache_hit_rate": round((self.cache_hits / self.total_calls * 100.0), 2) if self.total_calls else 0.0,
                "actual_cost_usd": round(self.actual_cost_usd, 6),
                "baseline_cost_usd": round(self.baseline_cost_usd, 6),
                "savings_usd": round(savings, 6),
                "cost_reduction_pct": round(reduction, 2),
            }


class SmartMultiLLMRouter:
    def __init__(self) -> None:
        self.providers: dict[str, BaseProvider] = {
            "anthropic": AnthropicProvider(),
            "google": GeminiProvider(),
            "openai": OpenAIProvider(),
            "ollama": OllamaProvider(),
            "groq": GroqProvider(),
            "xai": GroqProvider(),
        }
        self.analyzer = ComplexityAnalyzer()
        self.cache = ResponseCache(ttl_s=getattr(settings, "multi_llm_cache_ttl_s", 3600), max_items=3000)
        self.cost = CostTracker()
        self._routing_defaults = {
            "simple": ("groq", "llama-3.3-70b-versatile"),
            "medium": ("anthropic", settings.anthropic_sonnet_model or "claude-sonnet-4-5-20250929"),
            "complex": ("anthropic", settings.anthropic_opus_model or "claude-opus-4-5-20251101"),
        }

    def _choose(self, req: LLMRequest) -> tuple[str, str, str, float]:
        if req.preferred_provider and req.preferred_model:
            model = _normalize_model(req.preferred_provider, req.preferred_model)
            return req.preferred_provider, model, "explicit", 1.0

        level, score = self.analyzer.score(req.user)
        provider, model = self._routing_defaults[level]
        model_used = _normalize_model(provider, model)
        return provider, model_used, level, score

    async def execute(self, req: LLMRequest) -> dict[str, Any]:
        provider_name, model_used, route_level, complexity_score = self._choose(req)
        provider = self.providers.get(provider_name)
        if provider is None:
            raise MultiLLMError(f"Unsupported provider: {provider_name}")

        cache_enabled = bool(getattr(settings, "multi_llm_cache_enabled", True))
        cache_key = self.cache.make_key(provider=provider_name, model=model_used, system=req.system, user=req.user)
        if cache_enabled:
            cached = self.cache.get(cache_key)
            if cached is not None:
                cached["cached"] = True
                cached["trace_id"] = req.trace_id or cached.get("trace_id") or str(uuid.uuid4())
                cached["route_level"] = route_level
                cached["complexity_score"] = round(complexity_score, 3)
                self.cost.track(model_used=model_used, tokens=int(cached.get("tokens_used") or 0), cache_hit=True)
                return cached

        result = await provider.execute(
            model=model_used,
            system=req.system,
            user=req.user,
            trace_id=req.trace_id or str(uuid.uuid4()),
        )
        result["cached"] = False
        result["route_level"] = route_level
        result["complexity_score"] = round(complexity_score, 3)
        self.cost.track(model_used=result.get("model_used") or model_used, tokens=int(result.get("tokens_used") or 0), cache_hit=False)
        if cache_enabled:
            self.cache.put(cache_key, result)
        return result

    def cost_summary(self) -> dict[str, Any]:
        return self.cost.summary()


_router_singleton: SmartMultiLLMRouter | None = None
_router_lock = threading.Lock()


def get_multi_llm_router() -> SmartMultiLLMRouter:
    global _router_singleton
    if _router_singleton is not None:
        return _router_singleton
    with _router_lock:
        if _router_singleton is None:
            _router_singleton = SmartMultiLLMRouter()
    return _router_singleton
