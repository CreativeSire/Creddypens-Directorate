from __future__ import annotations

import sys
from pathlib import Path

# Allow running as `python scripts/test_multi_llm_router.py`
BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.llm.multi_router import CostTracker, LLMRequest, get_multi_llm_router
from app.settings import settings


def _assert(cond: bool, msg: str) -> None:
    if not cond:
        raise AssertionError(msg)


def main() -> int:
    # Force deterministic local test mode.
    settings.llm_mock = True
    settings.multi_llm_router_enabled = True
    settings.multi_llm_cache_enabled = True

    router = get_multi_llm_router()

    providers = [
        ("anthropic", "claude-sonnet-4-5-20250929"),
        ("google", "gemini-2.5-pro"),
        ("openai", "gpt-4.1-mini"),
        ("ollama", "llama3.1:8b"),
        ("groq", "llama-3.3-70b-versatile"),
    ]

    print("== Provider Class Checks ==")
    for p, m in providers:
        req = LLMRequest(system="You are a helpful assistant.", user=f"Say hello from {p}.", trace_id=f"t-{p}", preferred_provider=p, preferred_model=m)
        out = router.execute(req)
        _assert("response" in out and out["response"], f"{p} returned empty response")
        _assert((out.get("model_used") or "").startswith(f"{p}/"), f"{p} model_used mismatch: {out.get('model_used')}")
        print(f"PASS {p}: {out.get('model_used')}")

    # Reset cost tracking after provider smoke checks so savings metric reflects smart routing behavior.
    router.cost = CostTracker()

    print("\n== Smart Routing Checks ==")
    simple = router.execute(LLMRequest(system="sys", user="Summarize this in one sentence.", trace_id="simple"))
    medium = router.execute(LLMRequest(system="sys", user="Compare two options and provide a plan with risks.", trace_id="medium"))
    complex_q = "Provide architecture tradeoffs, root cause analysis, and optimization strategy for a multi-step system."
    complex_res = router.execute(LLMRequest(system="sys", user=complex_q, trace_id="complex"))
    print("simple:", simple.get("route_level"), simple.get("model_used"))
    print("medium:", medium.get("route_level"), medium.get("model_used"))
    print("complex:", complex_res.get("route_level"), complex_res.get("model_used"))
    _assert(simple.get("route_level") in {"simple", "explicit"}, "simple route level invalid")
    _assert(medium.get("route_level") in {"medium", "explicit"}, "medium route level invalid")
    _assert(complex_res.get("route_level") in {"complex", "explicit"}, "complex route level invalid")

    print("\n== Cache Checks ==")
    req = LLMRequest(system="sys", user="Cache me once.", trace_id="cache-1", preferred_provider="openai", preferred_model="gpt-4.1-mini")
    first = router.execute(req)
    second = router.execute(LLMRequest(system="sys", user="Cache me once.", trace_id="cache-2", preferred_provider="openai", preferred_model="gpt-4.1-mini"))
    _assert(first.get("cached") is False, "first response should not be cached")
    _assert(second.get("cached") is True, "second response should be cached")
    print("PASS cache hit")

    # Drive cost profile with simple workload to validate optimization target.
    for i in range(25):
        router.execute(LLMRequest(system="sys", user=f"Write one short bullet #{i}.", trace_id=f"bulk-{i}"))

    print("\n== Cost Tracking ==")
    stats = router.cost_summary()
    print(stats)
    _assert(stats["total_calls"] >= 1, "cost stats total_calls invalid")
    _assert(stats["cost_reduction_pct"] >= 80.0, f"cost reduction too low: {stats['cost_reduction_pct']}")
    print(f"PASS cost reduction: {stats['cost_reduction_pct']}%")

    print("\nALL TESTS PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
