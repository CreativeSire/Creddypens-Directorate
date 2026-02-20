from __future__ import annotations

import re


class SearchDetector:
    """Detect when queries likely require current web information."""

    SEARCH_INDICATORS = [
        "current",
        "currently",
        "latest",
        "recent",
        "today",
        "this week",
        "this month",
        "this year",
        "now",
        "right now",
        "news",
        "breaking",
        "announcement",
        "update",
        "happening",
        "price of",
        "stock price",
        "market",
        "trading at",
        "weather",
        "temperature",
        "forecast",
        "who is currently",
        "what is the status",
        "score",
        "game",
        "match",
        "tournament",
    ]

    SEARCH_QUESTION_PATTERNS = [
        r"what'?s?\s+(?:the\s+)?(?:latest|current|recent)",
        r"who\s+is\s+(?:the\s+)?current(?:ly)?",
        r"when\s+(?:is|was)\s+(?:the\s+)?(?:next|last)",
        r"how\s+much\s+(?:is|does|costs?)",
        r"what\s+happened\s+(?:today|yesterday|recently)",
        r"is\s+.+\s+still\b",
    ]

    def needs_search(self, message: str) -> bool:
        message_lower = (message or "").lower()
        if any(indicator in message_lower for indicator in self.SEARCH_INDICATORS):
            return True
        for pattern in self.SEARCH_QUESTION_PATTERNS:
            if re.search(pattern, message_lower):
                return True
        return False

    def extract_search_query(self, message: str) -> str:
        prefixes_to_remove = [
            "what is",
            "what's",
            "what are",
            "who is",
            "who's",
            "who are",
            "when is",
            "when was",
            "where is",
            "where's",
            "how much is",
            "how much does",
            "tell me about",
            "find",
            "search for",
            "can you",
            "could you",
            "please",
        ]

        cleaned = (message or "").strip()
        cleaned_lower = cleaned.lower()
        for prefix in prefixes_to_remove:
            if cleaned_lower.startswith(prefix):
                cleaned = cleaned[len(prefix) :].strip()
                break
        cleaned = cleaned.rstrip("?").strip()
        return cleaned if cleaned else (message or "").strip()


search_detector = SearchDetector()
