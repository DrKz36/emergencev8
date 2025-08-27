#requires -Version 5.1
Param(
  [string]$BaseUrl = "http://127.0.0.1:8000"
)
Write-Host ">> GET $BaseUrl/api/health"
try {
  $res = Invoke-RestMethod -Uri "$BaseUrl/api/health" -Method GET -TimeoutSec 10
  $res | ConvertTo-Json -Depth 5
} catch {
  Write-Error $_
}
