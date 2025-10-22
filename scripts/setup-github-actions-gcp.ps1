#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Configure GCP Service Account pour GitHub Actions CI/CD

.DESCRIPTION
    Crée un service account GCP avec les permissions nécessaires pour déployer via GitHub Actions.
    Génère une clé JSON à ajouter manuellement dans GitHub Secrets.

.PARAMETER ProjectId
    ID du projet GCP (défaut: emergence-469005)

.PARAMETER ServiceAccountName
    Nom du service account (défaut: github-actions)

.EXAMPLE
    .\setup-github-actions-gcp.ps1
    .\setup-github-actions-gcp.ps1 -ProjectId "mon-projet" -ServiceAccountName "ci-cd"
#>

param(
    [string]$ProjectId = "emergence-469005",
    [string]$ServiceAccountName = "github-actions"
)

$ErrorActionPreference = "Stop"

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "🔧 SETUP GCP SERVICE ACCOUNT POUR GITHUB ACTIONS" -ForegroundColor Cyan
Write-Host "============================================================`n" -ForegroundColor Cyan

# Vérifier que gcloud est installé
Write-Host "🔍 Vérification gcloud CLI..." -ForegroundColor Yellow
try {
    $gcloudVersion = gcloud version --format="value(Google Cloud SDK)" 2>$null
    Write-Host "✅ gcloud CLI détecté: version $gcloudVersion`n" -ForegroundColor Green
} catch {
    Write-Host "❌ gcloud CLI non trouvé. Installez-le: https://cloud.google.com/sdk/docs/install`n" -ForegroundColor Red
    exit 1
}

# Configurer le projet
Write-Host "🔧 Configuration du projet GCP: $ProjectId..." -ForegroundColor Yellow
try {
    gcloud config set project $ProjectId 2>$null | Out-Null
    Write-Host "✅ Projet configuré`n" -ForegroundColor Green
} catch {
    Write-Host "❌ Échec configuration projet. Vérifiez que le projet existe et que vous êtes authentifié.`n" -ForegroundColor Red
    exit 1
}

# Vérifier si le service account existe déjà
$ServiceAccountEmail = "$ServiceAccountName@$ProjectId.iam.gserviceaccount.com"
Write-Host "🔍 Vérification service account: $ServiceAccountEmail..." -ForegroundColor Yellow

$existingSA = gcloud iam service-accounts list --filter="email:$ServiceAccountEmail" --format="value(email)" 2>$null

if ($existingSA -eq $ServiceAccountEmail) {
    Write-Host "⚠️  Service account existe déjà: $ServiceAccountEmail" -ForegroundColor Yellow
    $choice = Read-Host "`n   Voulez-vous le réutiliser? (o/N)"
    if ($choice -ne "o" -and $choice -ne "O") {
        Write-Host "`n❌ Opération annulée.`n" -ForegroundColor Red
        exit 0
    }
    Write-Host "`n✅ Réutilisation du service account existant`n" -ForegroundColor Green
} else {
    Write-Host "📝 Création du service account..." -ForegroundColor Yellow
    try {
        gcloud iam service-accounts create $ServiceAccountName `
            --display-name="GitHub Actions - CI/CD" `
            --description="Service account for GitHub Actions CI/CD pipeline" 2>$null | Out-Null
        Write-Host "✅ Service account créé: $ServiceAccountEmail`n" -ForegroundColor Green
    } catch {
        Write-Host "❌ Échec création service account`n" -ForegroundColor Red
        exit 1
    }
}

# Donner les permissions nécessaires
Write-Host "🔐 Attribution des permissions IAM..." -ForegroundColor Yellow

$roles = @(
    "roles/run.admin",
    "roles/storage.admin",
    "roles/iam.serviceAccountUser",
    "roles/artifactregistry.writer"
)

foreach ($role in $roles) {
    Write-Host "   → $role..." -ForegroundColor Gray
    try {
        gcloud projects add-iam-policy-binding $ProjectId `
            --member="serviceAccount:$ServiceAccountEmail" `
            --role="$role" `
            --condition=None `
            --quiet 2>$null | Out-Null
    } catch {
        Write-Host "   ⚠️  Échec attribution $role (peut-être déjà présent)" -ForegroundColor Yellow
    }
}

Write-Host "✅ Permissions attribuées`n" -ForegroundColor Green

# Vérifier les permissions actuelles
Write-Host "🔍 Vérification des permissions..." -ForegroundColor Yellow
$currentRoles = gcloud projects get-iam-policy $ProjectId `
    --flatten="bindings[].members" `
    --filter="bindings.members:$ServiceAccountEmail" `
    --format="value(bindings.role)" 2>$null

if ($currentRoles) {
    Write-Host "✅ Permissions actuelles:" -ForegroundColor Green
    $currentRoles -split "`n" | ForEach-Object {
        Write-Host "   - $_" -ForegroundColor Cyan
    }
    Write-Host ""
} else {
    Write-Host "⚠️  Aucune permission trouvée (peut prendre quelques secondes à se propager)`n" -ForegroundColor Yellow
}

# Créer la clé JSON
$keyFileName = "github-actions-key.json"
$keyFilePath = Join-Path $PSScriptRoot $keyFileName

Write-Host "📄 Génération de la clé JSON..." -ForegroundColor Yellow

if (Test-Path $keyFilePath) {
    Write-Host "⚠️  Fichier $keyFileName existe déjà" -ForegroundColor Yellow
    $choice = Read-Host "   Voulez-vous le remplacer? (o/N)"
    if ($choice -ne "o" -and $choice -ne "O") {
        Write-Host "`n❌ Opération annulée. Utilisez le fichier existant.`n" -ForegroundColor Red
        exit 0
    }
    Remove-Item $keyFilePath -Force
}

try {
    gcloud iam service-accounts keys create $keyFilePath `
        --iam-account=$ServiceAccountEmail 2>$null | Out-Null
    Write-Host "✅ Clé JSON créée: $keyFilePath`n" -ForegroundColor Green
} catch {
    Write-Host "❌ Échec création clé JSON`n" -ForegroundColor Red
    exit 1
}

# Afficher les instructions pour GitHub
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "🎯 PROCHAINES ÉTAPES - GITHUB SECRETS" -ForegroundColor Cyan
Write-Host "============================================================`n" -ForegroundColor Cyan

Write-Host "1. Aller sur GitHub:" -ForegroundColor Yellow
Write-Host "   https://github.com/DrKz36/emergencev8/settings/secrets/actions`n" -ForegroundColor White

Write-Host "2. Cliquer sur 'New repository secret'`n" -ForegroundColor Yellow

Write-Host "3. Remplir:" -ForegroundColor Yellow
Write-Host "   - Name: GCP_SA_KEY" -ForegroundColor White
Write-Host "   - Secret: [Copier TOUT le contenu du fichier JSON ci-dessous]`n" -ForegroundColor White

Write-Host "4. Contenu à copier (fichier: $keyFilePath):" -ForegroundColor Yellow
Write-Host "------------------------------------------------------------" -ForegroundColor Gray
Get-Content $keyFilePath | Write-Host -ForegroundColor Cyan
Write-Host "------------------------------------------------------------`n" -ForegroundColor Gray

Write-Host "5. Cliquer sur 'Add secret' dans GitHub`n" -ForegroundColor Yellow

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "🔒 SÉCURITÉ" -ForegroundColor Cyan
Write-Host "============================================================`n" -ForegroundColor Cyan

Write-Host "⚠️  APRÈS avoir ajouté le secret dans GitHub:" -ForegroundColor Yellow
Write-Host "   1. Supprimer le fichier JSON local:" -ForegroundColor White
Write-Host "      Remove-Item $keyFilePath`n" -ForegroundColor Cyan

Write-Host "   2. Ne JAMAIS committer ce fichier dans Git`n" -ForegroundColor White

Write-Host "   3. Vérifier que .gitignore contient:" -ForegroundColor White
Write-Host "      *-key.json`n" -ForegroundColor Cyan

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "✅ CONFIGURATION TERMINÉE" -ForegroundColor Cyan
Write-Host "============================================================`n" -ForegroundColor Cyan

Write-Host "Service Account Email: $ServiceAccountEmail" -ForegroundColor Green
Write-Host "Clé JSON: $keyFilePath" -ForegroundColor Green
Write-Host "`nAprès avoir configuré le secret GitHub, testez avec:" -ForegroundColor Yellow
Write-Host "git push origin main" -ForegroundColor Cyan
Write-Host "`nLe workflow 'Deploy to Cloud Run' se lancera automatiquement.`n" -ForegroundColor White
