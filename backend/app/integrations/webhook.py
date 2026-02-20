from __future__ import annotations

import time
from typing import Any

import requests


class WebhookIntegration:
    def send_webhook(
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
        for attempt in range(1, max(1, attempts) + 1):
            try:
                response = requests.post(
                    target,
                    json=payload,
                    headers=request_headers,
                    timeout=max(3, int(timeout_s)),
                )
                if response.status_code < 400:
                    return {
                        "ok": True,
                        "status_code": response.status_code,
                        "attempt": attempt,
                        "response_text": response.text[:1000],
                    }
                last_error = RuntimeError(f"Webhook failed with HTTP {response.status_code}")
            except Exception as exc:  # noqa: BLE001
                last_error = exc

            if attempt < attempts:
                time.sleep(delay)
                delay = min(delay * 2, 8.0)

        raise RuntimeError(str(last_error) if last_error else "Webhook failed")


webhook_integration = WebhookIntegration()
