from __future__ import annotations

import os
import random
import uuid

from locust import HttpUser, between, task


ORG_ID = os.getenv("LOADTEST_ORG_ID", "org_loadtest")
AGENTS = [item.strip() for item in os.getenv("LOADTEST_AGENTS", "GREETER-01,SUPPORT-01,HUNTER-01").split(",") if item.strip()]


class CreddyPensUser(HttpUser):
    wait_time = between(0.5, 2.0)

    def on_start(self) -> None:
        self.org_id = f"{ORG_ID}_{uuid.uuid4().hex[:8]}"
        self.headers = {"X-Org-Id": self.org_id, "Content-Type": "application/json"}
        agent_codes = list(AGENTS)
        resp = self.client.get("/v1/agents", headers={"X-Org-Id": self.org_id}, name="GET /v1/agents (bootstrap)")
        if resp.status_code == 200:
            body = resp.json()
            discovered = []
            for item in body:
                code = item.get("agent_code") or item.get("code")
                if code:
                    discovered.append(code)
            if discovered:
                agent_codes = discovered[:3]
        self.agent_codes = agent_codes
        for agent_code in self.agent_codes:
            self.client.post(
                f"/v1/agents/{agent_code}/hire",
                headers={"X-Org-Id": self.org_id},
                name="POST /v1/agents/{agent_code}/hire",
            )

    @task(4)
    def health(self) -> None:
        self.client.get("/health", headers={"X-Org-Id": self.org_id}, name="GET /health")

    @task(3)
    def list_agents(self) -> None:
        self.client.get("/v1/agents", headers={"X-Org-Id": self.org_id}, name="GET /v1/agents")

    @task(2)
    def router_stats(self) -> None:
        self.client.get("/v1/llm/router/stats", headers={"X-Org-Id": self.org_id}, name="GET /v1/llm/router/stats")

    @task(5)
    def execute_agent(self) -> None:
        agent_code = random.choice(self.agent_codes or AGENTS)
        payload = {
            "org_id": self.org_id,
            "session_id": f"load-{uuid.uuid4().hex[:10]}",
            "message": "Provide a concise operational update in 2 bullet points.",
            "context": {"web_search": False, "doc_retrieval": False},
        }
        self.client.post(
            f"/v1/agents/{agent_code}/execute",
            json=payload,
            headers=self.headers,
            name="POST /v1/agents/{agent_code}/execute",
        )
