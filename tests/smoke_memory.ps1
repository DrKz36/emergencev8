[CmdletBinding()]
param(
  [string]$BaseUrl = "http://127.0.0.1:8000",
  [string]$IdToken = "",
  [int]$TimeoutSec = 15
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Assert-Url([string]$u) {
  if ([string]::IsNullOrWhiteSpace($u)) { throw "BaseUrl vide. Fournis -BaseUrl (ex: https://…run.app)" }
  if (-not ($u -match '^https?://')) { throw "BaseUrl invalide: $u" }
}

function Join-Url([string]$base, [string]$path) {
  if ($base.EndsWith("/")) { $base = $base.TrimEnd("/") }
  if ($path.StartsWith("/")) { return "$base$path" } else { return "$base/$path" }
}

function Show-Header([string]$title) { Write-Host ""; Write-Host "=== $title ===" -ForegroundColor Cyan }

Assert-Url $BaseUrl
$authHeaders = @{}
if (-not [string]::IsNullOrWhiteSpace($IdToken)) { $authHeaders["Authorization"] = "Bearer $IdToken" }

# -- Health (curl.exe pour éviter les soucis IWR/TLS) --
Show-Header "Health"
$healthUrl = Join-Url $BaseUrl "/api/health"
& curl.exe -sS -m $TimeoutSec -D - "$healthUrl" | Out-Host

# Helpers IWR JSON
function IwrJson([string]$method, [string]$url, [hashtable]$headers, $bodyObj) {
  $body = $null
  $ctype = $null
  if ($null -ne $bodyObj) {
    $body = ($bodyObj | ConvertTo-Json -Depth 6)
    $ctype = "application/json"
  }
  return Invoke-WebRequest -Method $method -Uri $url -Headers $headers -ContentType $ctype -Body $body -TimeoutSec $TimeoutSec -UseBasicParsing
}

# -- Memory: tend-garden (vide / {} / invalide) --
$tgUrl = Join-Url $BaseUrl "/api/memory/tend-garden"
Show-Header "Memory • tend-garden (body: empty)"
try { IwrJson -method "POST" -url $tgUrl -headers $authHeaders -bodyObj $null | Select-Object -Expand Content | Out-Host } catch { $_ | Out-Host }

Show-Header "Memory • tend-garden (body: {})"
try { IwrJson -method "POST" -url $tgUrl -headers $authHeaders -bodyObj @{} | Select-Object -Expand Content | Out-Host } catch { $_ | Out-Host }

Show-Header "Memory • tend-garden (body: invalid JSON string)"
try {
  $headers = $authHeaders.Clone()
  Invoke-WebRequest -Method POST -Uri $tgUrl -Headers $headers -ContentType "application/json" -Body '{"invalid":' -TimeoutSec $TimeoutSec -UseBasicParsing | Select-Object -Expand Content | Out-Host
} catch { $_ | Out-Host }

# -- Memory: status --
$statusUrl = Join-Url $BaseUrl "/api/memory/status"
Show-Header "Memory • status"
try { IwrJson -method "GET" -url $statusUrl -headers $authHeaders -bodyObj $null | Select-Object -Expand Content | Out-Host } catch { $_ | Out-Host }

Write-Host "`n=== DONE ==="
