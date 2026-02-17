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

$port = if ($env:PORT) { [int]$env:PORT } else { 8010 }
$baseUrl = "http://127.0.0.1:$port"

$proc = Start-Process -FilePath python -ArgumentList @("-m", "uvicorn", "app.main:app", "--port", "$port") -PassThru -WindowStyle Hidden
try {
  $deadline = (Get-Date).AddSeconds(30)
  do {
    try {
      $health = Invoke-WebRequest -Uri "$baseUrl/health" -TimeoutSec 2
      if ($health.StatusCode -eq 200) { break }
    } catch {
      Start-Sleep -Milliseconds 400
    }
  } while ((Get-Date) -lt $deadline)

  if (-not $health -or $health.StatusCode -ne 200) {
    throw "GET /health did not return 200"
  }

  $agentsResp = Invoke-WebRequest -Uri "$baseUrl/v1/agents" -TimeoutSec 10
  if ($agentsResp.StatusCode -ne 200) {
    throw "GET /v1/agents did not return 200"
  }

  $agents = $agentsResp.Content | ConvertFrom-Json
  $need = @("Author-01", "Assistant-01", "Greeter-01")

  foreach ($code in $need) {
    if ((@($agents.code) -notcontains $code)) {
      throw "Missing expected agent code: $code"
    }
    $a = $agents | Where-Object code -eq $code | Select-Object -First 1
    foreach ($f in @("code", "role", "department", "price_cents", "status", "llm_profile", "llm_provider", "llm_route")) {
      if (-not ($a.PSObject.Properties.Name -contains $f)) {
        throw "$code missing field: $f"
      }
    }
  }

  $comingSoonCount = @($agents | Where-Object status -eq "coming_soon").Count
  if ($comingSoonCount -lt 1) {
    throw "No coming_soon agents returned (expected at least 1)"
  }

  Write-Output "PASS: /health 200"
  Write-Output "PASS: /v1/agents 200"
  Write-Output "PASS: seeded agents present: $($need -join ', ')"
  Write-Output "PASS: coming_soon agents returned: $comingSoonCount"
} finally {
  if ($proc -and -not $proc.HasExited) {
    Stop-Process -Id $proc.Id -Force
  }
}
