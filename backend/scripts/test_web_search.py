from __future__ import annotations

import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.llm.litellm_client import execute_via_litellm
from app.llm.search_detector import search_detector
from app.tools.web_search import web_search


async def test_search_tool() -> None:
    print("=" * 60)
    print("TEST 1: Direct Web Search Tool")
    print("=" * 60)
    for query in ["Bitcoin price", "latest AI news", "weather in San Francisco"]:
        print(f"\nQuery: {query}")
        results = await web_search.search(query, num_results=3)
        formatted = web_search.format_results(results, max_results=2)
        print(f"Results:\n{formatted[:400]}\n")


def test_search_detector() -> None:
    print("\n" + "=" * 60)
    print("TEST 2: Search Detection")
    print("=" * 60)
    test_messages: list[tuple[str, bool]] = [
        ("What's the current price of Bitcoin?", True),
        ("Who is the current CEO of Microsoft?", True),
        ("What's the weather today?", True),
        ("Tell me about recent AI developments", True),
        ("What is 2+2?", False),
        ("Explain how photosynthesis works", False),
    ]
    for message, expected in test_messages:
        actual = search_detector.needs_search(message)
        status = "PASS" if actual == expected else "FAIL"
        print(f"\n{status} '{message}'")
        print(f"   Needs search: {actual} (expected: {expected})")
        if actual:
            print(f"   Search query: '{search_detector.extract_search_query(message)}'")


def test_integrated_execution() -> None:
    print("\n" + "=" * 60)
    print("TEST 3: Integrated Execution")
    print("=" * 60)
    test_cases = [
        ("What's the current weather in New York?", True),
        ("What's the latest news about AI regulations?", True),
        ("Hello, how can you help me?", False),
    ]
    for message, expect_search in test_cases:
        print(f"\nQuery: {message}")
        result = execute_via_litellm(
            provider="groq",
            model="llama-3.3-70b-versatile",
            system="You are a helpful assistant.",
            user=message,
            enable_search=True,
        )
        search_used = bool(result.get("search_used"))
        print(f"Search used: {search_used} (expected: {expect_search})")
        print(f"Model: {result.get('model_used')}")
        print(f"Response preview: {(result.get('response') or '')[:180]}...")


async def main() -> None:
    if not web_search.is_available():
        print("ERROR: SERPER_API_KEY not configured. Add it to backend/.env first.")
        return
    await test_search_tool()
    test_search_detector()
    await asyncio.to_thread(test_integrated_execution)
    print("\n" + "=" * 60)
    print("ALL TESTS COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
