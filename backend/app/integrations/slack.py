from __future__ import annotations

import aiohttp


class SlackIntegration:
    async def post_message(self, *, webhook_url: str, text: str) -> dict:
        if not webhook_url.strip():
            raise ValueError("Missing Slack webhook_url")
        async with aiohttp.ClientSession() as session:
            async with session.post(
                webhook_url.strip(),
                json={"text": text},
                timeout=15,
            ) as response:
                if response.status >= 400:
                    raise RuntimeError(f"Slack webhook failed ({response.status})")
                return {"ok": True, "status_code": response.status}


slack_integration = SlackIntegration()
