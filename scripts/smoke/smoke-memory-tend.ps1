#requires -Version 5.1
Param(
  [string]$BaseUrl = "http://127.0.0.1:8000",
  [string]$UserId  = "FG"
)
$headers = @{ "X-User-Id" = $UserId }
Write-Host ">> POST $BaseUrl/api/memory/tend-garden"
try {
  $res = Invoke-RestMethod -Uri "$BaseUrl/api/memory/tend-garden" -Method POST -Headers $headers -TimeoutSec 30
  $res | ConvertTo-Json -Depth 6
} catch {
  Write-Error $_
}
