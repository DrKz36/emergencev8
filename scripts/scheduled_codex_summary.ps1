# Scheduled Codex Summary - Génère résumé Guardian pour Codex GPT (Task Scheduler)
# Exécuté toutes les 6h automatiquement

$ErrorActionPreference = "Stop"
$RepoRoot = "C:\dev\emergenceV8"

# Timestamp
$timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "SCHEDULED CODEX SUMMARY GENERATION" -ForegroundColor Cyan
Write-Host "Timestamp: $timestamp" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

# Changer vers le repo
Set-Location $RepoRoot

# Activer virtualenv Python si présent
if (Test-Path ".venv\Scripts\Activate.ps1") {
    Write-Host "🐍 Activation virtualenv..." -ForegroundColor Yellow
    & .\.venv\Scripts\Activate.ps1
}

# 1. Régénérer rapports Guardian frais
Write-Host "📊 Génération rapports Guardian frais..." -ForegroundColor Yellow

# ProdGuardian
Write-Host "  ☁️  ProdGuardian (production Cloud Run)..." -ForegroundColor Gray
try {
    python claude-plugins/integrity-docs-guardian/scripts/check_prod_logs.py 2>&1 | Out-Null
    Write-Host "    ✅ ProdGuardian OK" -ForegroundColor Green
} catch {
    Write-Host "    ⚠️  ProdGuardian failed: $_" -ForegroundColor Yellow
}

# Anima (DocKeeper)
Write-Host "  📚 Anima (documentation)..." -ForegroundColor Gray
try {
    python claude-plugins/integrity-docs-guardian/scripts/scan_docs.py 2>&1 | Out-Null
    Write-Host "    ✅ Anima OK" -ForegroundColor Green
} catch {
    Write-Host "    ⚠️  Anima failed: $_" -ForegroundColor Yellow
}

# Neo (IntegrityWatcher)
Write-Host "  🔐 Neo (intégrité)..." -ForegroundColor Gray
try {
    python claude-plugins/integrity-docs-guardian/scripts/check_integrity.py 2>&1 | Out-Null
    Write-Host "    ✅ Neo OK" -ForegroundColor Green
} catch {
    Write-Host "    ⚠️  Neo failed: $_" -ForegroundColor Yellow
}

# Nexus (Coordinator)
Write-Host "  🎯 Nexus (rapport unifié)..." -ForegroundColor Gray
try {
    python claude-plugins/integrity-docs-guardian/scripts/master_orchestrator.py 2>&1 | Out-Null
    Write-Host "    ✅ Nexus OK" -ForegroundColor Green
} catch {
    Write-Host "    ⚠️  Nexus failed: $_" -ForegroundColor Yellow
}

Write-Host ""

# 2. Générer résumé Codex
Write-Host "📝 Génération résumé Codex GPT..." -ForegroundColor Yellow
try {
    python scripts/generate_codex_summary.py
    Write-Host "✅ Résumé Codex généré: reports/codex_summary.md" -ForegroundColor Green
} catch {
    Write-Host "❌ Erreur génération résumé Codex: $_" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "✅ SUCCÈS - Résumé Codex mis à jour" -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Cyan

# Log dans fichier
$logFile = "logs/scheduled_codex_summary.log"
if (-not (Test-Path (Split-Path $logFile))) {
    New-Item -ItemType Directory -Path (Split-Path $logFile) -Force | Out-Null
}
Add-Content -Path $logFile -Value "[$timestamp] Résumé Codex généré avec succès"

exit 0
