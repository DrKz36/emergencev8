#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Déploie manuellement Emergence sur Cloud Run via GitHub Actions

.DESCRIPTION
    Déclenche le workflow GitHub Actions de déploiement manuellement.
    Évite les deploys automatiques à chaque push (contrôle total).

.PARAMETER Reason
    Raison du déploiement (optionnel, pour traçabilité)

.EXAMPLE
    .\scripts\deploy-manual.ps1
    .\scripts\deploy-manual.ps1 -Reason "Fix bug auth critique"

.NOTES
    Prérequis:
    - GitHub CLI installée (gh)
    - Authentifié (gh auth login)
    - Branch main à jour (git pull)
#>

param(
    [string]$Reason = ""
)

$ErrorActionPreference = "Stop"

Write-Host "🚀 Déploiement manuel Emergence sur Cloud Run" -ForegroundColor Cyan
Write-Host ""

# Vérifier que gh CLI est installé
if (-not (Get-Command gh -ErrorAction SilentlyContinue)) {
    Write-Host "❌ GitHub CLI (gh) n'est pas installé" -ForegroundColor Red
    Write-Host "   Installez-le: winget install GitHub.cli" -ForegroundColor Yellow
    exit 1
}

# Vérifier l'authentification gh
$authStatus = gh auth status 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ GitHub CLI non authentifié" -ForegroundColor Red
    Write-Host "   Exécutez: gh auth login" -ForegroundColor Yellow
    exit 1
}

# Vérifier qu'on est sur la branche main
$currentBranch = git rev-parse --abbrev-ref HEAD
if ($currentBranch -ne "main") {
    Write-Host "⚠️  Vous n'êtes pas sur la branche main (actuellement: $currentBranch)" -ForegroundColor Yellow
    $continue = Read-Host "Voulez-vous quand même déployer depuis main? (o/N)"
    if ($continue -ne "o" -and $continue -ne "O") {
        Write-Host "❌ Déploiement annulé" -ForegroundColor Red
        exit 0
    }
}

# S'assurer que main est à jour
Write-Host "📥 Mise à jour de la branche main..." -ForegroundColor Yellow
git fetch origin main
git checkout main
git pull origin main

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Impossible de mettre à jour la branche main" -ForegroundColor Red
    exit 1
}

# Afficher le commit qui sera déployé
$lastCommit = git log -1 --oneline
Write-Host ""
Write-Host "📦 Commit à déployer:" -ForegroundColor Cyan
Write-Host "   $lastCommit" -ForegroundColor White
Write-Host ""

if ($Reason) {
    Write-Host "📝 Raison: $Reason" -ForegroundColor Cyan
    Write-Host ""
}

# Confirmation finale
$confirm = Read-Host "Confirmer le déploiement? (o/N)"
if ($confirm -ne "o" -and $confirm -ne "O") {
    Write-Host "❌ Déploiement annulé" -ForegroundColor Red
    exit 0
}

# Déclencher le workflow GitHub Actions
Write-Host ""
Write-Host "🚀 Déclenchement du workflow GitHub Actions..." -ForegroundColor Green

if ($Reason) {
    gh workflow run deploy.yml -f reason="$Reason"
} else {
    gh workflow run deploy.yml
}

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Erreur lors du déclenchement du workflow" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "✅ Workflow de déploiement déclenché!" -ForegroundColor Green
Write-Host ""
Write-Host "📊 Pour suivre le déploiement:" -ForegroundColor Cyan
Write-Host "   1. Via GitHub UI: https://github.com/votre-repo/actions" -ForegroundColor White
Write-Host "   2. Via CLI: gh run watch" -ForegroundColor White
Write-Host ""
Write-Host "🔗 App déployée sur: https://emergence-app-469005.europe-west1.run.app" -ForegroundColor Cyan
Write-Host ""

# Proposer de suivre le déploiement
$watch = Read-Host "Voulez-vous suivre le déploiement en temps réel? (o/N)"
if ($watch -eq "o" -or $watch -eq "O") {
    Write-Host ""
    Write-Host "👀 Suivi du déploiement..." -ForegroundColor Yellow
    gh run watch
}
