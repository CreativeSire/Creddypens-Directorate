from __future__ import annotations

import logging
import re
from typing import Any

from sqlalchemy import text

from app.db import SessionLocal

logger = logging.getLogger(__name__)


class DocumentSearchTool:
    """Search internal knowledge base using Postgres full-text search."""

    _DOC_HINTS = (
        "hours",
        "pricing",
        "price",
        "security",
        "privacy",
        "policy",
        "refund",
        "cancel",
        "onboarding",
        "getting started",
        "integration",
        "integrations",
        "compliance",
        "department",
        "agents",
        "capabilities",
        "support",
    )

    def needs_docs(self, message: str) -> bool:
        content = (message or "").strip().lower()
        if not content:
            return False
        if len(content.split()) < 3:
            return False
        if any(hint in content for hint in self._DOC_HINTS):
            return True
        return bool(re.search(r"\b(what|how|when|where)\b", content))

    def search(
        self,
        query: str,
        limit: int = 5,
        category: str | None = None,
    ) -> list[dict[str, Any]]:
        q = (query or "").strip()
        if not q:
            return []
        cap = max(1, min(int(limit), 10))
        try:
            with SessionLocal() as db:
                if category:
                    rows = db.execute(
                        text(
                            """
                            select
                              id,
                              title,
                              content,
                              category,
                              tags,
                              source_url,
                              ts_rank(
                                to_tsvector('english', coalesce(title, '') || ' ' || coalesce(content, '')),
                                plainto_tsquery('english', :query)
                              ) as rank
                            from knowledge_base
                            where is_active = true
                              and category = :category
                              and to_tsvector('english', coalesce(title, '') || ' ' || coalesce(content, ''))
                                  @@ plainto_tsquery('english', :query)
                            order by rank desc
                            limit :limit;
                            """
                        ),
                        {"query": q, "category": category, "limit": cap},
                    ).mappings().all()
                else:
                    rows = db.execute(
                        text(
                            """
                            select
                              id,
                              title,
                              content,
                              category,
                              tags,
                              source_url,
                              ts_rank(
                                to_tsvector('english', coalesce(title, '') || ' ' || coalesce(content, '')),
                                plainto_tsquery('english', :query)
                              ) as rank
                            from knowledge_base
                            where is_active = true
                              and to_tsvector('english', coalesce(title, '') || ' ' || coalesce(content, ''))
                                  @@ plainto_tsquery('english', :query)
                            order by rank desc
                            limit :limit;
                            """
                        ),
                        {"query": q, "limit": cap},
                    ).mappings().all()

                results = [dict(row) for row in rows]
                if results:
                    return results

                # Fallback for natural-language queries that don't match FTS well.
                tokens = [token for token in re.findall(r"[a-zA-Z0-9]+", q.lower()) if len(token) >= 4][:6]
                if not tokens:
                    return []
                or_clauses = []
                params: dict[str, Any] = {"limit": cap}
                for idx, token in enumerate(tokens, start=1):
                    key = f"t{idx}"
                    params[key] = f"%{token}%"
                    or_clauses.append(f"(lower(title) like :{key} or lower(content) like :{key})")
                where = " or ".join(or_clauses)
                fallback_rows = db.execute(
                    text(
                        f"""
                        select id, title, content, category, tags, source_url, 0.01 as rank
                        from knowledge_base
                        where is_active = true
                          and ({where})
                        order by updated_at desc
                        limit :limit;
                        """
                    ),
                    params,
                ).mappings().all()
                return [dict(row) for row in fallback_rows]
        except Exception as e:
            logger.error("Document search error: %s", e)
            return []

    def format_results(self, results: list[dict[str, Any]], max_content_length: int = 300) -> str:
        if not results:
            return "No relevant internal documents found."

        formatted = ["--- Internal Knowledge Base ---"]
        for index, doc in enumerate(results, 1):
            title = str(doc.get("title") or "Untitled")
            content = str(doc.get("content") or "")
            category = str(doc.get("category") or "General")
            if len(content) > max_content_length:
                content = content[:max_content_length].rstrip() + "..."
            formatted.append(
                f"\n{index}. {title}\n"
                f"   Category: {category}\n"
                f"   Content: {content}"
            )
            source = str(doc.get("source_url") or "").strip()
            if source:
                formatted.append(f"   Source: {source}")
            formatted.append("")

        return "\n".join(formatted).strip()

    def is_available(self) -> bool:
        try:
            with SessionLocal() as db:
                count = db.execute(
                    text("select count(*)::int from knowledge_base where is_active = true;")
                ).scalar_one()
            return int(count or 0) > 0
        except Exception:
            return False


doc_search = DocumentSearchTool()
