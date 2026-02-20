from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from typing import Any

import requests


@dataclass
class CheckResult:
    name: str
    ok: bool
    detail: str


def run(base_url: str, org_id: str, timeout: int, strict_pdf: bool) -> int:
    base = base_url.rstrip("/")

    def req(method: str, path: str, **kwargs: Any) -> requests.Response:
        headers = kwargs.pop("headers", {}) or {}
        headers.setdefault("X-Org-Id", org_id)
        return requests.request(method, f"{base}{path}", timeout=timeout, headers=headers, **kwargs)

    checks: list[CheckResult] = []

    try:
        health = req("GET", "/health")
        checks.append(CheckResult("health", health.status_code == 200, f"status={health.status_code}"))
    except Exception as exc:
        checks.append(CheckResult("health", False, str(exc)))
        health = None  # noqa: F841

    try:
        agents = req("GET", "/v1/agents")
        if agents.status_code == 200:
            body = agents.json()
            count = len(body) if isinstance(body, list) else 0
            checks.append(CheckResult("agents", count > 0, f"count={count}"))
            first_agent = (body[0].get("code") or body[0].get("agent_code")) if count else "GREETER-01"
        else:
            checks.append(CheckResult("agents", False, f"status={agents.status_code}"))
            first_agent = "GREETER-01"
    except Exception as exc:
        checks.append(CheckResult("agents", False, str(exc)))
        first_agent = "GREETER-01"

    for name, path in [
        ("router_stats", "/v1/llm/router/stats"),
        ("dashboard_stats", f"/v1/organizations/{org_id}/dashboard-stats"),
        ("analytics_overview", f"/v1/organizations/{org_id}/analytics/overview?days=30"),
        ("analytics_costs", f"/v1/organizations/{org_id}/analytics/costs?days=30"),
        ("analytics_activity", f"/v1/organizations/{org_id}/analytics/activity?days=30"),
    ]:
        try:
            response = req("GET", path)
            checks.append(CheckResult(name, response.status_code == 200, f"status={response.status_code}"))
        except Exception as exc:
            checks.append(CheckResult(name, False, str(exc)))

    interaction_id: str | None = None
    try:
        _ = req("POST", f"/v1/agents/{first_agent}/hire")
        execute = req(
            "POST",
            f"/v1/agents/{first_agent}/execute",
            json={
                "org_id": org_id,
                "session_id": "staging-smoke",
                "message": "Return a concise answer with one markdown table of two rows.",
                "context": {"output_format": "markdown", "web_search": False, "doc_retrieval": False},
            },
        )
        if execute.status_code == 200:
            payload = execute.json()
            interaction_id = payload.get("interaction_id")
            ok = bool(payload.get("response")) and bool(interaction_id)
            checks.append(
                CheckResult(
                    "agent_execute",
                    ok,
                    f"status=200 provider={payload.get('provider')} model={payload.get('model_used')}",
                )
            )
        else:
            checks.append(CheckResult("agent_execute", False, f"status={execute.status_code}"))
    except Exception as exc:
        checks.append(CheckResult("agent_execute", False, str(exc)))

    if interaction_id:
        for name, path, expected in [
            ("export_email", f"/v1/interactions/{interaction_id}/email", {200}),
            ("export_csv", f"/v1/interactions/{interaction_id}/csv", {200, 400}),
            ("export_pdf", f"/v1/interactions/{interaction_id}/pdf", {200, 503} if not strict_pdf else {200}),
        ]:
            try:
                response = req("GET", path)
                checks.append(CheckResult(name, response.status_code in expected, f"status={response.status_code}"))
            except Exception as exc:
                checks.append(CheckResult(name, False, str(exc)))
    else:
        checks.append(CheckResult("export_email", False, "skipped: no interaction_id"))
        checks.append(CheckResult("export_csv", False, "skipped: no interaction_id"))
        checks.append(CheckResult("export_pdf", False, "skipped: no interaction_id"))

    passed = sum(1 for c in checks if c.ok)
    print("\nSTAGING SMOKE TEST")
    print("=" * 72)
    for c in checks:
        print(f"{'PASS' if c.ok else 'FAIL'}  {c.name:20s}  {c.detail}")
    print("-" * 72)
    print(f"TOTAL: {passed}/{len(checks)} passed")
    print(
        json.dumps(
            {"base_url": base, "org_id": org_id, "passed": passed, "total": len(checks), "checks": [c.__dict__ for c in checks]},
            indent=2,
        )
    )
    return 0 if passed == len(checks) else 1


def main() -> int:
    parser = argparse.ArgumentParser(description="Run staging/production smoke test matrix.")
    parser.add_argument("--base-url", required=True, help="Base URL, e.g. https://creddypens.com")
    parser.add_argument("--org-id", default="org_smoke")
    parser.add_argument("--timeout", type=int, default=25)
    parser.add_argument("--strict-pdf", action="store_true", help="Fail if PDF export is not 200")
    args = parser.parse_args()
    return run(base_url=args.base_url, org_id=args.org_id, timeout=args.timeout, strict_pdf=args.strict_pdf)


if __name__ == "__main__":
    raise SystemExit(main())
