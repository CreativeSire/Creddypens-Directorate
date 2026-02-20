from __future__ import annotations

import time
from collections import defaultdict, deque
from dataclasses import dataclass

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware


@dataclass(frozen=True)
class _LimitRule:
    max_requests: int
    window_seconds: int


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(
        self,
        app,
        *,
        enabled: bool = True,
        execute_limit_per_minute: int = 20,
        default_limit_per_minute: int = 200,
    ) -> None:
        super().__init__(app)
        self.enabled = enabled
        self.execute_rule = _LimitRule(max_requests=max(1, execute_limit_per_minute), window_seconds=60)
        self.default_rule = _LimitRule(max_requests=max(1, default_limit_per_minute), window_seconds=60)
        self._requests: dict[str, deque[float]] = defaultdict(deque)

    def _is_execute_endpoint(self, path: str) -> bool:
        return path.startswith("/v1/agents/") and (path.endswith("/execute") or path.endswith("/execute/stream"))

    def _resolve_key(self, request: Request, scope: str) -> str:
        org_id = request.headers.get("X-Org-Id", "").strip() or "anonymous"
        ip = request.client.host if request.client else "unknown"
        return f"{scope}:{org_id}:{ip}"

    def _check(self, key: str, rule: _LimitRule) -> tuple[bool, int]:
        now = time.time()
        bucket = self._requests[key]
        cutoff = now - rule.window_seconds
        while bucket and bucket[0] < cutoff:
            bucket.popleft()
        if len(bucket) >= rule.max_requests:
            retry_after = max(1, int(rule.window_seconds - (now - bucket[0])))
            return False, retry_after
        bucket.append(now)
        return True, 0

    async def dispatch(self, request: Request, call_next):
        if not self.enabled or request.url.path in {"/health", "/docs", "/openapi.json"}:
            return await call_next(request)

        if self._is_execute_endpoint(request.url.path):
            key = self._resolve_key(request, "execute")
            allowed, retry_after = self._check(key, self.execute_rule)
            if not allowed:
                return JSONResponse(
                    status_code=429,
                    content={"detail": "Rate limit exceeded for execute endpoint"},
                    headers={"Retry-After": str(retry_after)},
                )
        else:
            key = self._resolve_key(request, "default")
            allowed, retry_after = self._check(key, self.default_rule)
            if not allowed:
                return JSONResponse(
                    status_code=429,
                    content={"detail": "Rate limit exceeded"},
                    headers={"Retry-After": str(retry_after)},
                )

        return await call_next(request)

