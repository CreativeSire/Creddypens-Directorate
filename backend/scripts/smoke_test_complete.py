from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass
from typing import Any

import requests


BASE_URL = os.getenv("SMOKE_BASE_URL", "http://localhost:8010").rstrip("/")
ORG_ID = os.getenv("SMOKE_ORG_ID", "org_smoke")
TIMEOUT = int(os.getenv("SMOKE_TIMEOUT_S", "20"))


@dataclass
class CheckResult:
    name: str
    ok: bool
    detail: str


def _request(method: str, path: str, **kwargs: Any) -> requests.Response:
    headers = kwargs.pop("headers", {}) or {}
    headers.setdefault("X-Org-Id", ORG_ID)
    return requests.request(method, f"{BASE_URL}{path}", timeout=TIMEOUT, headers=headers, **kwargs)


def check_health() -> CheckResult:
    response = _request("GET", "/health")
    ok = response.status_code == 200
    return CheckResult("health", ok, f"status={response.status_code}")


def check_agents() -> tuple[CheckResult, list[dict[str, Any]]]:
    response = _request("GET", "/v1/agents")
    if response.status_code != 200:
        return CheckResult("agents_list", False, f"status={response.status_code}"), []
    data = response.json()
    ok = isinstance(data, list) and len(data) > 0
    detail = f"count={len(data) if isinstance(data, list) else 'invalid'}"
    return CheckResult("agents_list", ok, detail), data if isinstance(data, list) else []


def check_router_stats() -> CheckResult:
    response = _request("GET", "/v1/llm/router/stats")
    ok = response.status_code == 200
    return CheckResult("router_stats", ok, f"status={response.status_code}")


def check_execute(agent_code: str) -> CheckResult:
    hire_response = _request("POST", f"/v1/agents/{agent_code}/hire")
    if hire_response.status_code not in {200, 201}:
        return CheckResult("agent_execute", False, f"hire_status={hire_response.status_code}")

    payload = {
        "org_id": ORG_ID,
        "session_id": "smoke-session",
        "message": "Give me a short greeting and one sentence on how you can help.",
        "context": {"web_search": False, "doc_retrieval": False},
    }
    response = _request("POST", f"/v1/agents/{agent_code}/execute", json=payload)
    if response.status_code != 200:
        return CheckResult("agent_execute", False, f"status={response.status_code} body={response.text[:120]}")

    body = response.json()
    ok = bool(body.get("response")) and "interaction_id" in body
    detail = f"provider={body.get('provider')} cached={body.get('cached')} search={body.get('search_used')} docs={body.get('docs_used')}"
    return CheckResult("agent_execute", ok, detail)


def check_memory_crud() -> CheckResult:
    create_payload = {"memory_type": "preference", "memory_key": "smoke_tone", "memory_value": "concise"}
    create = _request("POST", f"/v1/organizations/{ORG_ID}/memories", json=create_payload)
    if create.status_code != 200:
        return CheckResult("memory_crud", False, f"create_status={create.status_code}")
    memory_id = create.json().get("memory_id")
    if not memory_id:
        return CheckResult("memory_crud", False, "create_response_missing_memory_id")
    update = _request("PUT", f"/v1/memories/{memory_id}", json={"memory_value": "formal concise"})
    list_response = _request("GET", f"/v1/organizations/{ORG_ID}/memories")
    delete_response = _request("DELETE", f"/v1/memories/{memory_id}")
    ok = update.status_code == 200 and list_response.status_code == 200 and delete_response.status_code == 200
    return CheckResult(
        "memory_crud",
        ok,
        f"update={update.status_code} list={list_response.status_code} delete={delete_response.status_code}",
    )


def check_file_endpoints() -> CheckResult:
    files_response = _request("GET", f"/v1/organizations/{ORG_ID}/files")
    ok = files_response.status_code == 200
    return CheckResult("file_list_endpoint", ok, f"status={files_response.status_code}")


def check_workflow_validate() -> CheckResult:
    payload = {
        "workflow_definition": {
            "start_step_id": "step1",
            "steps": [
                {"id": "step1", "agent_code": "GREETER-01", "input": "Draft welcome", "next": "step2"},
                {"id": "step2", "agent_code": "GREETER-01", "input": "Improve clarity"},
            ],
        }
    }
    response = _request("POST", "/v1/workflows/validate", json=payload)
    ok = response.status_code == 200
    return CheckResult("workflow_validate", ok, f"status={response.status_code}")


def run() -> int:
    checks: list[CheckResult] = []
    agents: list[dict[str, Any]] = []

    def _safe(name: str, fn):
        try:
            return fn()
        except requests.RequestException as exc:
            return CheckResult(name, False, f"{type(exc).__name__}: {exc}")
        except Exception as exc:
            return CheckResult(name, False, f"{type(exc).__name__}: {exc}")

    checks.append(_safe("health", check_health))
    agent_result = _safe("agents_list", check_agents)
    if isinstance(agent_result, tuple):
        checks.append(agent_result[0])
        agents = agent_result[1]
    else:
        checks.append(agent_result)
    checks.append(_safe("router_stats", check_router_stats))
    checks.append(_safe("memory_crud", check_memory_crud))
    checks.append(_safe("file_list_endpoint", check_file_endpoints))
    checks.append(_safe("workflow_validate", check_workflow_validate))
    if agents:
        selected_agent = agents[0].get("agent_code") or agents[0].get("code") or "GREETER-01"
        checks.append(_safe("agent_execute", lambda: check_execute(selected_agent)))
    else:
        checks.append(CheckResult("agent_execute", False, "skipped: no agents available"))

    passed = sum(1 for c in checks if c.ok)
    print("\nCOMPLETE SMOKE TEST MATRIX")
    print("=" * 72)
    for check in checks:
        print(f"{'PASS' if check.ok else 'FAIL'}  {check.name:24s}  {check.detail}")
    print("-" * 72)
    print(f"TOTAL: {passed}/{len(checks)} passed")

    output = {
        "base_url": BASE_URL,
        "org_id": ORG_ID,
        "passed": passed,
        "total": len(checks),
        "checks": [check.__dict__ for check in checks],
    }
    print(json.dumps(output, indent=2))
    return 0 if passed == len(checks) else 1


if __name__ == "__main__":
    raise SystemExit(run())
