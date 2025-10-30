#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Réapplique le binding IAM public sur le service Cloud Run de prod.

.DESCRIPTION
    Déclenche le workflow GitHub Actions `Restore Cloud Run IAM Access`.
    Utile quand le binding `allUsers → roles/run.invoker` a sauté et que la prod répond 403.

.PARAMETER Reason
    Motif (optionnel) loggué dans l'exécution du workflow.

.EXAMPLE
    .\scripts\restore-cloud-run-iam.ps1
    .\scripts\restore-cloud-run-iam.ps1 -Reason "Hotfix 403 prod"

.NOTES
    Prérequis:
    - GitHub CLI installée (gh)
    - Authentifié (`gh auth login`)
    - Accès au repo `DrKz36/emergencev8`
#>

param(
    [string]$Reason = ""
)

$ErrorActionPreference = "Stop"

Write-Host "🛠️  Hotfix Cloud Run IAM (emergence-app)" -ForegroundColor Cyan
Write-Host "" 

if (-not (Get-Command gh -ErrorAction SilentlyContinue)) {
    Write-Host "❌ GitHub CLI (gh) n'est pas installé" -ForegroundColor Red
    Write-Host "   Installe-le avant de continuer: https://cli.github.com" -ForegroundColor Yellow
    exit 1
}

$authStatus = gh auth status 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ GitHub CLI non authentifié" -ForegroundColor Red
    Write-Host "   Exécute: gh auth login" -ForegroundColor Yellow
    exit 1
}

Write-Host "🚀 Déclenchement du workflow 'Restore Cloud Run IAM Access'" -ForegroundColor Green
if ($Reason) {
    Write-Host "ℹ️  Raison: $Reason" -ForegroundColor Yellow
    gh workflow run cloud-run-iam-restore.yml -f reason="$Reason"
} else {
    gh workflow run cloud-run-iam-restore.yml
}

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Erreur lors du déclenchement du workflow" -ForegroundColor Red
    exit 1
}

Write-Host "✅ Workflow lancé. Il remettra allUsers → roles/run.invoker et vérifiera /health" -ForegroundColor Green
Write-Host "" 

$watch = Read-Host "Suivre le run en temps réel? (o/N)"
if ($watch -eq "o" -or $watch -eq "O") {
    Write-Host "👀 Suivi du workflow..." -ForegroundColor Cyan
    gh run watch
}
