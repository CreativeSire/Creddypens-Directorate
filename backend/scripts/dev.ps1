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

$port = if ($env:PORT) { [int]$env:PORT } else { 8010 }

if (-not $env:DATABASE_URL) {
  $env:DATABASE_URL = "postgresql+psycopg://postgres:postgres@localhost:5433/creddypens"
}

python -m uvicorn app.main:app --reload --port $port
