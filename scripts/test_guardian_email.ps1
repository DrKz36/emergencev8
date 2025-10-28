# ============================================================================
# TEST GUARDIAN EMAIL - Quick Test
# ============================================================================
# Teste l'envoi d'emails Guardian vers emergence.app.ch@gmail.com
# ============================================================================

$ErrorActionPreference = "Stop"
$repoRoot = "C:\dev\emergenceV8"
$scriptsDir = "$repoRoot\claude-plugins\integrity-docs-guardian\scripts"

Set-Location $repoRoot

Write-Host "`n================================================================" -ForegroundColor Cyan
Write-Host "📧 TEST GUARDIAN EMAIL" -ForegroundColor Cyan
Write-Host "================================================================`n" -ForegroundColor Cyan

Write-Host "Recipient: emergence.app.ch@gmail.com" -ForegroundColor White
Write-Host ""

# Vérifier que le script existe
if (-not (Test-Path "$scriptsDir\send_guardian_reports_email.py")) {
    Write-Host "❌ Script send_guardian_reports_email.py introuvable" -ForegroundColor Red
    exit 1
}

# Vérifier les variables d'environnement
$envFile = "$repoRoot\.env"
if (-not (Test-Path $envFile)) {
    Write-Host "❌ Fichier .env introuvable" -ForegroundColor Red
    exit 1
}

Write-Host "✅ Fichier .env trouvé" -ForegroundColor Green
Write-Host "✅ Script d'envoi trouvé" -ForegroundColor Green
Write-Host ""

# Tester l'envoi
Write-Host "📤 Envoi des rapports Guardian..." -ForegroundColor Yellow
Write-Host ""

$result = & python "$scriptsDir\send_guardian_reports_email.py" --to "emergence.app.ch@gmail.com" 2>&1
$exitCode = $LASTEXITCODE

Write-Host ""
Write-Host "================================================================" -ForegroundColor Cyan

if ($exitCode -eq 0) {
    Write-Host "✅ EMAIL ENVOYÉ AVEC SUCCÈS" -ForegroundColor Green
    Write-Host ""
    Write-Host "📧 Vérifie ta boîte mail: emergence.app.ch@gmail.com" -ForegroundColor White
} else {
    Write-Host "❌ ÉCHEC DE L'ENVOI" -ForegroundColor Red
    Write-Host ""
    Write-Host "Sortie:" -ForegroundColor Yellow
    Write-Host $result -ForegroundColor Gray
}

Write-Host "================================================================`n" -ForegroundColor Cyan

exit $exitCode
