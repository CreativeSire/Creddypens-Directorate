param(
  [Parameter(Mandatory = $true)][string]$BackendUrl,
  [Parameter(Mandatory = $false)][string]$FrontendUrl = "",
  [Parameter(Mandatory = $false)][string]$AgentCode = "Author-01"
)

$ErrorActionPreference = "Stop"

function Step($name) {
  Write-Host ""
  Write-Host "==> $name" -ForegroundColor Cyan
}

function Pass($msg) {
  Write-Host "PASS: $msg" -ForegroundColor Green
}

function Fail($msg) {
  Write-Host "FAIL: $msg" -ForegroundColor Red
}

function Get-Json([string]$url, [hashtable]$headers = @{}) {
  return Invoke-RestMethod -Method Get -Uri $url -Headers $headers -TimeoutSec 60
}

function Post-Json([string]$url, [object]$body, [hashtable]$headers = @{}) {
  $payload = $body | ConvertTo-Json -Depth 20
  return Invoke-RestMethod -Method Post -Uri $url -Body $payload -ContentType "application/json" -Headers $headers -TimeoutSec 120
}

$BackendUrl = $BackendUrl.TrimEnd("/")
$FrontendUrl = $FrontendUrl.TrimEnd("/")
$orgId = "org_smoke_$([guid]::NewGuid().ToString('N').Substring(0, 10))"
$sessionId = "smoke_$([guid]::NewGuid().ToString('N').Substring(0, 8))"
$headers = @{ "X-Org-Id" = $orgId }

$script:results = @()
function Add-Result($name, $ok, $detail) {
  $script:results += [PSCustomObject]@{ Step = $name; Ok = $ok; Detail = $detail }
}

try {
  Step "1) Backend health"
  $health = Get-Json "$BackendUrl/health"
  if ($health.ok -eq $true) {
    Pass "health ok=true, llm_mock=$($health.llm_mock)"
    Add-Result "health" $true "ok=$($health.ok), llm_mock=$($health.llm_mock)"
  } else {
    throw "health response invalid"
  }

  Step "2) Agents catalog"
  $agents = Get-Json "$BackendUrl/v1/agents"
  if (-not $agents -or $agents.Count -lt 1) { throw "No agents returned" }
  $activeCount = @($agents | Where-Object { $_.status -eq "active" }).Count
  $target = $agents | Where-Object { $_.code -ieq $AgentCode } | Select-Object -First 1
  if (-not $target) { throw "Target agent '$AgentCode' not found" }
  Pass "agents=$($agents.Count), active=$activeCount, target=$($target.code)"
  Add-Result "agents" $true "count=$($agents.Count), active=$activeCount, target=$($target.code)"

  Step "3) Optional frontend basic availability"
  if ($FrontendUrl) {
    # UseBasicParsing avoids legacy IE/COM dependencies that can throw null-reference errors on Windows.
    $homeResp = Invoke-WebRequest -UseBasicParsing -Method Get -Uri $FrontendUrl -TimeoutSec 60
    if ($homeResp.StatusCode -eq 200) {
      Pass "frontend home status=200"
      Add-Result "frontend-home" $true "status=200"
    } else {
      throw "frontend returned status $($homeResp.StatusCode)"
    }
  } else {
    Pass "frontend URL not provided, skipped"
    Add-Result "frontend-home" $true "skipped"
  }

  Step "4) Checkout/hire"
  $checkout = Post-Json "$BackendUrl/v1/agents/$($target.code)/checkout" @{} $headers
  if (-not $checkout.success) { throw "Checkout failed" }
  Pass "mode=$($checkout.mode), message=$($checkout.message)"
  Add-Result "checkout" $true "mode=$($checkout.mode)"

  Step "5) Org hired agents"
  $orgAgents = Get-Json "$BackendUrl/v1/organizations/$orgId/agents?include_stats=1" $headers
  $hired = $orgAgents | Where-Object { $_.agent.agent_code -ieq $target.code }
  if (-not $hired) { throw "Hired agent record not found for $($target.code)" }
  Pass "hired agent found for $($target.code)"
  Add-Result "org-agents" $true "hired-found=$($target.code)"

  Step "6) Execute chat"
  $executeBody = @{
    message    = "Write a 3-sentence intro for a coffee shop called Brewed Awakening."
    context    = @{
      company_name = "Brewed Awakening"
      tone         = "friendly"
      additional   = @{ source = "prod-smoke" }
    }
    session_id = $sessionId
  }
  $exec = Post-Json "$BackendUrl/v1/agents/$($target.code)/execute" $executeBody $headers
  if (-not $exec.response -or $exec.response.Trim().Length -lt 2) { throw "Empty execute response" }
  Pass "model=$($exec.model_used), latency_ms=$($exec.latency_ms), trace=$($exec.trace_id)"
  Add-Result "execute" $true "latency_ms=$($exec.latency_ms), model=$($exec.model_used)"

  Step "7) Dashboard stats"
  $stats = Get-Json "$BackendUrl/v1/organizations/$orgId/dashboard-stats" $headers
  if ($null -eq $stats.hired_agents_count) { throw "Stats missing hired_agents_count" }
  Pass "hired=$($stats.hired_agents_count), tasks_week=$($stats.tasks_this_week), avg_ms=$($stats.avg_response_time_ms)"
  Add-Result "dashboard-stats" $true "hired=$($stats.hired_agents_count), tasks_week=$($stats.tasks_this_week)"

  Step "8) Academy status"
  $academy = Get-Json "$BackendUrl/v1/organizations/$orgId/academy-status" $headers
  if ($null -eq $academy.avg_quality_score) { throw "Academy status missing avg_quality_score" }
  Pass "in_training=$($academy.agents_in_training), avg_quality=$($academy.avg_quality_score)"
  Add-Result "academy-status" $true "avg_quality=$($academy.avg_quality_score)"

  Step "9) Director recommend"
  $recommend = Post-Json "$BackendUrl/v1/director/recommend" @{ message = "I need help managing customer inquiries"; org_id = $orgId } @{}
  if (-not $recommend.recommendations -or $recommend.recommendations.Count -lt 1) { throw "No recommendations returned" }
  Pass "recommendations=$($recommend.recommendations.Count)"
  Add-Result "director-recommend" $true "recs=$($recommend.recommendations.Count)"

} catch {
  $msg = $_.Exception.Message
  try {
    $resp = $_.Exception.Response
    if ($resp -and $resp.GetResponseStream()) {
      $reader = New-Object System.IO.StreamReader($resp.GetResponseStream())
      $body = $reader.ReadToEnd()
      if ($body) { $msg = "$msg | body=$body" }
    }
  } catch { }
  Fail $msg
  Add-Result "fatal" $false $msg
}

Write-Host ""
Write-Host "========== PROD SMOKE SUMMARY ==========" -ForegroundColor Yellow
$script:results | ForEach-Object {
  $status = if ($_.Ok) { "PASS" } else { "FAIL" }
  $color = if ($_.Ok) { "Green" } else { "Red" }
  Write-Host ("{0,-20} {1,-5} {2}" -f $_.Step, $status, $_.Detail) -ForegroundColor $color
}

$failed = @($script:results | Where-Object { -not $_.Ok }).Count
if ($failed -gt 0) {
  exit 1
}
exit 0
