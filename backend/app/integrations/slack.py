from __future__ import annotations

import requests


class SlackIntegration:
    def post_message(self, *, webhook_url: str, text: str) -> dict:
        if not webhook_url.strip():
            raise ValueError("Missing Slack webhook_url")
        response = requests.post(
            webhook_url.strip(),
            json={"text": text},
            timeout=15,
        )
        if response.status_code >= 400:
            raise RuntimeError(f"Slack webhook failed ({response.status_code})")
        return {"ok": True, "status_code": response.status_code}


slack_integration = SlackIntegration()
