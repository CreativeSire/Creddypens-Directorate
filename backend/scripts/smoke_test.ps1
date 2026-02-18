$ErrorActionPreference = "Stop"

Set-Location (Split-Path $PSScriptRoot -Parent)

if (-not $env:DATABASE_URL) {
  if (Test-Path ".env") {
    Get-Content ".env" | ForEach-Object {
      if ($_ -match "^(?<k>[A-Za-z_][A-Za-z0-9_]*)=(?<v>.*)$") {
        $k = $Matches["k"]
        $v = $Matches["v"]
        if (-not [string]::IsNullOrWhiteSpace($k)) {
          Set-Item -Path ("env:" + $k) -Value $v
        }
      }
    }
  }
}

if (-not $env:DATABASE_URL) {
  $env:DATABASE_URL = "postgresql+psycopg://postgres:postgres@localhost:5433/creddypens"
}

python .\scripts\seed_agents.py

@'
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

health = client.get("/health")
if health.status_code != 200:
    raise SystemExit("GET /health did not return 200")

agents_resp = client.get("/v1/agents")
if agents_resp.status_code != 200:
    raise SystemExit("GET /v1/agents did not return 200")

agents = agents_resp.json()
required_codes = {"Author-01", "Assistant-01", "Greeter-01"}

for code in required_codes:
    found = next((agent for agent in agents if agent.get("code") == code), None)
    if not found:
        raise SystemExit(f"Missing expected agent code: {code}")
    for field in ("code", "role", "human_name", "tagline", "department", "price_cents", "status", "capabilities", "ideal_for"):
        if field not in found:
            raise SystemExit(f"{code} missing field: {field}")

if len(agents) < 42:
    raise SystemExit(f"Expected at least 42 agents, got {len(agents)}")

inactive_count = sum(1 for agent in agents if agent.get("status") != "active")
if inactive_count != 0:
    raise SystemExit(f"Expected all agents active, found {inactive_count} non-active rows")

print("PASS: /health 200")
print("PASS: /v1/agents 200")
print("PASS: seeded agents present: Author-01, Assistant-01, Greeter-01")
print(f"PASS: all agents active ({len(agents)} total)")
'@ | python -
