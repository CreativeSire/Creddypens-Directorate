from __future__ import annotations

import os
import random

from locust import HttpUser, between, task


ORG_ID = os.getenv("LOADTEST_ORG_ID", "org_loadtest")
AGENTS = [item.strip() for item in os.getenv("LOADTEST_AGENTS", "GREETER-01,SUPPORT-01,HUNTER-01").split(",") if item.strip()]


class CreddyPensUser(HttpUser):
    wait_time = between(0.5, 2.0)

    def on_start(self) -> None:
        self.headers = {"X-Org-Id": ORG_ID, "Content-Type": "application/json"}

    @task(4)
    def health(self) -> None:
        self.client.get("/health", headers={"X-Org-Id": ORG_ID}, name="GET /health")

    @task(3)
    def list_agents(self) -> None:
        self.client.get("/v1/agents", headers={"X-Org-Id": ORG_ID}, name="GET /v1/agents")

    @task(2)
    def router_stats(self) -> None:
        self.client.get("/v1/llm/router/stats", headers={"X-Org-Id": ORG_ID}, name="GET /v1/llm/router/stats")

    @task(5)
    def execute_agent(self) -> None:
        agent_code = random.choice(AGENTS)
        payload = {
            "org_id": ORG_ID,
            "message": "Provide a concise operational update in 2 bullet points.",
            "context": {"web_search": False, "doc_retrieval": False},
        }
        self.client.post(
            f"/v1/agents/{agent_code}/execute",
            json=payload,
            headers=self.headers,
            name="POST /v1/agents/{agent_code}/execute",
        )

