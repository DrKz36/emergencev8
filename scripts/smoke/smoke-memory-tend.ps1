#requires -Version 5.1
Param(
  [string]$BaseUrl = "http://127.0.0.1:8000",
  [string]$UserId  = "FG",
  [string]$SessionId,
  [string]$AuthToken = $env:EMERGENCE_ID_TOKEN
)

if (-not $SessionId -or -not $SessionId.Trim()) {
  $SessionId = "tend-" + ([Guid]::NewGuid().ToString("N"))
} else {
  $SessionId = $SessionId.Trim()
}

$headers = @{
  "X-User-Id"    = $UserId
  "X-Session-Id" = $SessionId
}
if ($AuthToken) {
  $headers["Authorization"] = "Bearer $AuthToken"
}

Write-Host ">> POST $BaseUrl/api/memory/tend-garden" -ForegroundColor Cyan
Write-Host "   Session ID : $SessionId" -ForegroundColor DarkGray
try {
  $res = Invoke-RestMethod -Uri "$BaseUrl/api/memory/tend-garden" -Method POST -Headers $headers -TimeoutSec 30 -ContentType "application/json" -Body "{}"
  $res | ConvertTo-Json -Depth 6
} catch {
  Write-Error $_
}
