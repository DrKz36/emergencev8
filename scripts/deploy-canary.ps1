<#
.SYNOPSIS
    Script de déploiement canary automatisé pour ÉMERGENCE sur Google Cloud Run

.DESCRIPTION
    Ce script automatise le processus de déploiement canary :
    1. Build de l'image Docker
    2. Push vers Google Container Registry
    3. Déploiement sans trafic (--no-traffic)
    4. Tests de validation
    5. Routage progressif du trafic (10% → 25% → 50% → 100%)

.PARAMETER SkipBuild
    Skip la phase de build Docker (utilise l'image latest existante)

.PARAMETER SkipTests
    Skip les tests de validation

.PARAMETER TrafficPercent
    Pourcentage de trafic initial à router (par défaut: 10)

.EXAMPLE
    .\deploy-canary.ps1
    Déploiement canary complet avec toutes les étapes

.EXAMPLE
    .\deploy-canary.ps1 -SkipBuild
    Déploiement canary en utilisant l'image latest existante

.EXAMPLE
    .\deploy-canary.ps1 -TrafficPercent 25
    Déploiement canary avec 25% de trafic initial
#>

param(
    [switch]$SkipBuild,
    [switch]$SkipTests,
    [int]$TrafficPercent = 10
)

$ErrorActionPreference = "Stop"

# Configuration
$PROJECT_ID = "emergence-469005"
$REGION = "europe-west1"
$SERVICE_NAME = "emergence-app"
$IMAGE_BASE = "europe-west1-docker.pkg.dev/$PROJECT_ID/emergence-repo/$SERVICE_NAME"
$TIMESTAMP = Get-Date -Format "yyyyMMdd-HHmmss"
$IMAGE_TAG = "${IMAGE_BASE}:${TIMESTAMP}"
$IMAGE_LATEST = "${IMAGE_BASE}:latest"
$CANARY_TAG = "canary-$(Get-Date -Format 'yyyyMMdd')"

Write-Host "════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "🚀 ÉMERGENCE - Déploiement Canary Automatisé" -ForegroundColor Cyan
Write-Host "════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""
Write-Host "Project:  $PROJECT_ID" -ForegroundColor White
Write-Host "Service:  $SERVICE_NAME" -ForegroundColor White
Write-Host "Region:   $REGION" -ForegroundColor White
Write-Host "Tag:      $TIMESTAMP" -ForegroundColor White
Write-Host "Traffic:  $TrafficPercent% (initial)" -ForegroundColor White
Write-Host ""

# Étape 1 : Build Docker
if (-not $SkipBuild) {
    Write-Host "═══ Étape 1/6 : Build de l'image Docker ═══" -ForegroundColor Yellow
    Write-Host ""

    docker build -t $IMAGE_LATEST -t $IMAGE_TAG .

    if ($LASTEXITCODE -ne 0) {
        Write-Host "❌ Erreur lors du build Docker" -ForegroundColor Red
        exit 1
    }

    Write-Host "✅ Build réussi" -ForegroundColor Green
    Write-Host ""
} else {
    Write-Host "⏭️  Étape 1/6 : Build Docker skippé (utilisation de l'image latest)" -ForegroundColor Gray
    Write-Host ""
}

# Étape 2 : Push vers GCR
Write-Host "═══ Étape 2/6 : Push vers Google Container Registry ═══" -ForegroundColor Yellow
Write-Host ""

docker push $IMAGE_LATEST

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Erreur lors du push de l'image latest" -ForegroundColor Red
    exit 1
}

if (-not $SkipBuild) {
    docker push $IMAGE_TAG

    if ($LASTEXITCODE -ne 0) {
        Write-Host "❌ Erreur lors du push de l'image timestampée" -ForegroundColor Red
        exit 1
    }
}

Write-Host "✅ Push réussi" -ForegroundColor Green
Write-Host ""

# Étape 3 : Déploiement sans trafic
Write-Host "═══ Étape 3/6 : Déploiement sans trafic (--no-traffic) ═══" -ForegroundColor Yellow
Write-Host ""

$deployOutput = gcloud run deploy $SERVICE_NAME `
    --image=$IMAGE_TAG `
    --region=$REGION `
    --project=$PROJECT_ID `
    --no-traffic `
    --tag=$CANARY_TAG `
    2>&1 | Out-String

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Erreur lors du déploiement" -ForegroundColor Red
    Write-Host $deployOutput
    exit 1
}

# Extraire le nom de la révision
$revisionName = ($deployOutput | Select-String -Pattern "revision \[(.*?)\]").Matches.Groups[1].Value

if (-not $revisionName) {
    Write-Host "⚠️  Impossible d'extraire le nom de la révision" -ForegroundColor Yellow
    Write-Host "Output du déploiement :"
    Write-Host $deployOutput

    # Fallback : récupérer la dernière révision
    $revisionName = (gcloud run revisions list `
        --service=$SERVICE_NAME `
        --region=$REGION `
        --project=$PROJECT_ID `
        --limit=1 `
        --format="value(name)") | Out-String
    $revisionName = $revisionName.Trim()
}

Write-Host "✅ Révision déployée : $revisionName" -ForegroundColor Green
Write-Host "📋 Tag canary : $CANARY_TAG" -ForegroundColor Cyan
Write-Host ""

# Récupérer l'URL canary
$canaryUrl = "https://$CANARY_TAG---$SERVICE_NAME-47nct44nma-ew.a.run.app"

# Étape 4 : Tests de validation
if (-not $SkipTests) {
    Write-Host "═══ Étape 4/6 : Tests de validation ═══" -ForegroundColor Yellow
    Write-Host ""

    Write-Host "🔍 Test 1 : Health check..." -ForegroundColor Cyan
    $healthResponse = curl -s "$canaryUrl/api/health" | ConvertFrom-Json

    if ($healthResponse.status -eq "ok") {
        Write-Host "  ✅ Health check OK" -ForegroundColor Green
    } else {
        Write-Host "  ❌ Health check échoué" -ForegroundColor Red
        Write-Host "  Response: $($healthResponse | ConvertTo-Json)"
        exit 1
    }

    Write-Host ""
    Write-Host "🔍 Test 2 : Fichiers statiques..." -ForegroundColor Cyan
    $staticResponse = curl -s -I "$canaryUrl/src/frontend/main.js" | Select-String -Pattern "HTTP"

    if ($staticResponse -match "200") {
        Write-Host "  ✅ Fichiers statiques OK" -ForegroundColor Green
    } else {
        Write-Host "  ❌ Fichiers statiques inaccessibles" -ForegroundColor Red
        exit 1
    }

    Write-Host ""
    Write-Host "🔍 Test 3 : Vérification des logs (erreurs)..." -ForegroundColor Cyan
    $errorLogs = gcloud logging read `
        "resource.type=cloud_run_revision AND resource.labels.service_name=$SERVICE_NAME AND resource.labels.revision_name=$revisionName AND severity>=ERROR" `
        --limit=5 `
        --project=$PROJECT_ID `
        --freshness=5m `
        --format="value(textPayload,jsonPayload.message)" `
        2>$null

    if ([string]::IsNullOrWhiteSpace($errorLogs)) {
        Write-Host "  ✅ Aucune erreur détectée" -ForegroundColor Green
    } else {
        Write-Host "  ⚠️  Erreurs détectées :" -ForegroundColor Yellow
        Write-Host $errorLogs

        $continue = Read-Host "Continuer le déploiement ? (y/N)"
        if ($continue -ne "y") {
            Write-Host "❌ Déploiement annulé par l'utilisateur" -ForegroundColor Red
            exit 1
        }
    }

    Write-Host ""
    Write-Host "✅ Tous les tests sont passés" -ForegroundColor Green
    Write-Host ""
} else {
    Write-Host "⏭️  Étape 4/6 : Tests de validation skippés" -ForegroundColor Gray
    Write-Host ""
}

# Étape 5 : Routage du trafic
Write-Host "═══ Étape 5/6 : Routage du trafic ($TrafficPercent%) ═══" -ForegroundColor Yellow
Write-Host ""

gcloud run services update-traffic $SERVICE_NAME `
    --to-revisions="${revisionName}=${TrafficPercent}" `
    --region=$REGION `
    --project=$PROJECT_ID

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Erreur lors du routage du trafic" -ForegroundColor Red
    exit 1
}

Write-Host "✅ Trafic routé : $TrafficPercent% vers la nouvelle révision" -ForegroundColor Green
Write-Host ""

# Étape 6 : Résumé et prochaines étapes
Write-Host "═══ Étape 6/6 : Résumé et prochaines étapes ═══" -ForegroundColor Yellow
Write-Host ""
Write-Host "✅ Déploiement canary réussi !" -ForegroundColor Green
Write-Host ""
Write-Host "📊 État actuel :" -ForegroundColor Cyan
Write-Host "  • Révision canary : $revisionName" -ForegroundColor White
Write-Host "  • Trafic canary : $TrafficPercent%" -ForegroundColor White
Write-Host "  • URL canary : $canaryUrl" -ForegroundColor White
Write-Host ""
Write-Host "🔍 Surveillance (recommandé : 15-30 min) :" -ForegroundColor Cyan
Write-Host "  • Logs en temps réel :" -ForegroundColor White
Write-Host "    gcloud logging tail ""resource.type=cloud_run_revision AND resource.labels.service_name=$SERVICE_NAME"" --project=$PROJECT_ID" -ForegroundColor Gray
Write-Host ""
Write-Host "  • Dashboard métriques :" -ForegroundColor White
Write-Host "    https://console.cloud.google.com/run/detail/$REGION/$SERVICE_NAME/metrics" -ForegroundColor Gray
Write-Host ""
Write-Host "📈 Prochaines phases de déploiement :" -ForegroundColor Cyan
Write-Host "  • Phase 2 (25%) : gcloud run services update-traffic $SERVICE_NAME --to-revisions=$revisionName=25 --region=$REGION --project=$PROJECT_ID" -ForegroundColor Gray
Write-Host "  • Phase 3 (50%) : gcloud run services update-traffic $SERVICE_NAME --to-revisions=$revisionName=50 --region=$REGION --project=$PROJECT_ID" -ForegroundColor Gray
Write-Host "  • Phase 4 (100%) : gcloud run services update-traffic $SERVICE_NAME --to-latest --region=$REGION --project=$PROJECT_ID" -ForegroundColor Gray
Write-Host ""
Write-Host "🔄 Rollback (si nécessaire) :" -ForegroundColor Cyan
Write-Host "  gcloud run services update-traffic $SERVICE_NAME --to-revisions=emergence-app-00366-jp2=100 --region=$REGION --project=$PROJECT_ID" -ForegroundColor Gray
Write-Host ""
Write-Host "════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "✅ Script terminé avec succès" -ForegroundColor Green
Write-Host "════════════════════════════════════════════════════════════" -ForegroundColor Cyan
