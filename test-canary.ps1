$CANARY_URL = "https://canary-beta-2-1-1---emergence-app-47nct44nma-ew.a.run.app"

Write-Host "`n════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "Testing Canary Deployment - beta-2.1.1" -ForegroundColor Cyan
Write-Host "════════════════════════════════════════════`n" -ForegroundColor Cyan

Write-Host "Canary URL: $CANARY_URL`n" -ForegroundColor White

# Test 1: Health Check
Write-Host "=== Test 1: Health Check ===" -ForegroundColor Yellow
try {
    $response = Invoke-RestMethod -Uri "$CANARY_URL/api/health" -Method Get -TimeoutSec 10
    Write-Host "✅ Health check passed" -ForegroundColor Green
    Write-Host "Status: $($response.status)" -ForegroundColor White
    if ($response.version) {
        Write-Host "Version: $($response.version)" -ForegroundColor White
    }
} catch {
    Write-Host "❌ Health check failed: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

Write-Host ""

# Test 2: Main Page
Write-Host "=== Test 2: Main Page ===" -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "$CANARY_URL/" -UseBasicParsing -TimeoutSec 10
    Write-Host "✅ Main page accessible (HTTP $($response.StatusCode))" -ForegroundColor Green
} catch {
    Write-Host "❌ Main page failed: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

Write-Host ""

# Test 3: Static Files
Write-Host "=== Test 3: Static Files ===" -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "$CANARY_URL/src/frontend/main.js" -UseBasicParsing -TimeoutSec 10
    Write-Host "✅ Static files accessible (HTTP $($response.StatusCode))" -ForegroundColor Green
} catch {
    Write-Host "❌ Static files failed: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "════════════════════════════════════════════" -ForegroundColor Green
Write-Host "✅ All tests passed successfully!" -ForegroundColor Green
Write-Host "════════════════════════════════════════════" -ForegroundColor Green
Write-Host ""
