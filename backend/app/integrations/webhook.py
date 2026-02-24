from __future__ import annotations

import asyncio
from typing import Any

import aiohttp


class WebhookIntegration:
    async def send_webhook(
        self,
        *,
        url: str,
        payload: dict[str, Any],
        headers: dict[str, str] | None = None,
        timeout_s: int = 12,
        attempts: int = 3,
    ) -> dict:
        target = (url or "").strip()
        if not target:
            raise ValueError("Missing webhook url")

        request_headers = {"Content-Type": "application/json"}
        if headers:
            request_headers.update({str(key): str(value) for key, value in headers.items()})

        delay = 1.0
        last_error: Exception | None = None
        async with aiohttp.ClientSession() as session:
            for attempt in range(1, max(1, attempts) + 1):
                try:
                    async with session.post(
                        target,
                        json=payload,
                        headers=request_headers,
                        timeout=max(3, int(timeout_s)),
                    ) as response:
                        if response.status < 400:
                            # Read text to ensure connection closes cleanly
                            text = await response.text()
                            return {
                                "ok": True,
                                "status_code": response.status,
                                "attempt": attempt,
                                "response_text": text[:1000],
                            }
                        last_error = RuntimeError(f"Webhook failed with HTTP {response.status}")
                except Exception as exc:  # noqa: BLE001
                    last_error = exc

                if attempt < attempts:
                    await asyncio.sleep(delay)
                    delay = min(delay * 2, 8.0)

        raise RuntimeError(str(last_error) if last_error else "Webhook failed")


webhook_integration = WebhookIntegration()
