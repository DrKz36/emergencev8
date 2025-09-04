# C:\dev\emergenceV8\tests\smoke_prod.ps1
Param([string]$Region="europe-west1", [string]$Service="emergence-app")

Write-Host "== Smoke prod Cloud Run =="

$RUNURL = (gcloud run services describe $Service --region $Region --format="value(status.url)")
if (-not $RUNURL) { throw "Service URL introuvable." }
$TOKEN  = Get-Content .\id_token.txt

"Service URL: $RUNURL"

"GET /api/health ->"
curl.exe -si "$RUNURL/api/health" | Select-String "HTTP/"

"GET /api/memory/status ->"
curl.exe -si "$RUNURL/api/memory/status" -H "Authorization: Bearer $TOKEN" | Select-String "HTTP/"

"POST /api/memory/tend-garden ->"
curl.exe -si -X POST "$RUNURL/api/memory/tend-garden" `
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" `
  -d "{}" | Select-String "HTTP/"

$READY = (gcloud run services describe $Service --region $Region --format="value(status.latestReadyRevisionName)")
"`nLogs ($READY):"
gcloud beta run revisions logs read $READY --region $Region --limit=160 --format="value(textPayload)" `
| Select-String -Pattern "Started server process","Application startup complete","Uvicorn running on http://0.0.0.0:8080"
