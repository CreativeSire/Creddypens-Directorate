from __future__ import annotations

import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.llm.litellm_client import execute_via_litellm
from app.tools.document_search import doc_search


def test_document_search_tool() -> None:
    print("=" * 60)
    print("TEST 1: Direct Document Search")
    print("=" * 60)
    for query in ["pricing", "hours of operation", "data security", "how to get started"]:
        print(f"\nQuery: '{query}'")
        results = doc_search.search(query, limit=2)
        formatted = doc_search.format_results(results, max_content_length=200)
        print(f"Found {len(results)} documents")
        print(formatted[:500] if formatted else "No results")


async def test_integrated_execution() -> None:
    print("\n" + "=" * 60)
    print("TEST 2: Integrated Execution with Document Retrieval")
    print("=" * 60)
    test_cases = [
        ("What are your hours of operation?", True),
        ("What's your pricing structure?", True),
        ("Tell me about your security and data privacy", True),
        ("Hello, nice to meet you!", False),
    ]
    for message, expect_docs in test_cases:
        print(f"\nQuery: {message}")
        result = await asyncio.to_thread(
            execute_via_litellm,
            provider="groq",
            model="llama-3.3-70b-versatile",
            system="You are a helpful assistant.",
            user=message,
            enable_search=False,
            enable_docs=True,
        )
        docs_used = bool(result.get("docs_used"))
        print(f"Docs used: {docs_used} (expected: {expect_docs})")
        print(f"Response preview: {(result.get('response') or '')[:250]}...")
        print("PASS" if docs_used == expect_docs else "FAIL")


async def main() -> None:
    if not doc_search.is_available():
        print("Knowledge base appears empty. Run: python scripts/seed_knowledge_base.py")
        return
    test_document_search_tool()
    await test_integrated_execution()
    print("\n" + "=" * 60)
    print("ALL DOCUMENT SEARCH TESTS COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())

