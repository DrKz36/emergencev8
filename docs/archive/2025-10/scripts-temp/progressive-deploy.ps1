<#
.SYNOPSIS
    Script de déploiement progressif pour ÉMERGENCE beta-2.1.1

.DESCRIPTION
    Augmente progressivement le trafic vers la nouvelle révision:
    - Étape 1: 25% trafic
    - Étape 2: 50% trafic
    - Étape 3: 100% trafic

.PARAMETER Step
    Étape du déploiement (25, 50, ou 100)
#>

param(
    [Parameter(Mandatory=$true)]
    [ValidateSet("25", "50", "100")]
    [string]$Step
)

$PROJECT_ID = "emergence-469005"
$REGION = "europe-west1"
$SERVICE_NAME = "emergence-app"
$NEW_REVISION = "emergence-app-00462-rag"
$OLD_REVISION = "emergence-app-00458-fiy"

Write-Host "`n════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  ÉMERGENCE - Déploiement Progressif beta-2.1.1" -ForegroundColor Cyan
Write-Host "════════════════════════════════════════════════════════════`n" -ForegroundColor Cyan

Write-Host "Configuration:" -ForegroundColor White
Write-Host "  Project:       $PROJECT_ID" -ForegroundColor White
Write-Host "  Service:       $SERVICE_NAME" -ForegroundColor White
Write-Host "  Region:        $REGION" -ForegroundColor White
Write-Host "  New Revision:  $NEW_REVISION (beta-2.1.1)" -ForegroundColor Green
Write-Host "  Old Revision:  $OLD_REVISION" -ForegroundColor Yellow
Write-Host "  Target Split:  $Step% → New | $((100 - [int]$Step))% → Old`n" -ForegroundColor Cyan

# Confirmation
$confirm = Read-Host "Continuer avec le déploiement à $Step% ? (y/N)"
if ($confirm -ne "y" -and $confirm -ne "Y") {
    Write-Host "❌ Déploiement annulé" -ForegroundColor Red
    exit 0
}

Write-Host "`n⏳ Mise à jour du routage du trafic..." -ForegroundColor Yellow

if ($Step -eq "100") {
    # Déploiement complet - utiliser --to-latest
    Write-Host "   Routage de 100% du trafic vers la dernière révision..." -ForegroundColor Cyan

    gcloud run services update-traffic $SERVICE_NAME `
        --to-latest `
        --region=$REGION `
        --project=$PROJECT_ID
} else {
    # Déploiement partiel
    $oldPercent = 100 - [int]$Step

    gcloud run services update-traffic $SERVICE_NAME `
        --to-revisions="${NEW_REVISION}=${Step},${OLD_REVISION}=${oldPercent}" `
        --region=$REGION `
        --project=$PROJECT_ID
}

if ($LASTEXITCODE -eq 0) {
    Write-Host "`n✅ Mise à jour du trafic réussie !`n" -ForegroundColor Green

    # Afficher l'état actuel
    Write-Host "📊 État actuel du trafic:" -ForegroundColor Cyan
    gcloud run services describe $SERVICE_NAME `
        --region=$REGION `
        --project=$PROJECT_ID `
        --format="table(status.traffic.revisionName,status.traffic.percent,status.traffic.tag)"

    Write-Host "`n📈 Recommandations:" -ForegroundColor Yellow

    if ($Step -eq "25") {
        Write-Host "  • Surveiller les métriques pendant 10-15 minutes" -ForegroundColor White
        Write-Host "  • Si tout va bien, passer à 50%:" -ForegroundColor White
        Write-Host "    pwsh .\progressive-deploy.ps1 -Step 50`n" -ForegroundColor Gray
    } elseif ($Step -eq "50") {
        Write-Host "  • Surveiller les métriques pendant 15-20 minutes" -ForegroundColor White
        Write-Host "  • Si tout va bien, passer à 100%:" -ForegroundColor White
        Write-Host "    pwsh .\progressive-deploy.ps1 -Step 100`n" -ForegroundColor Gray
    } else {
        Write-Host "  • Déploiement complet terminé !" -ForegroundColor Green
        Write-Host "  • Surveiller les logs et métriques" -ForegroundColor White
        Write-Host "  • URL production: https://emergence-app-47nct44nma-ew.a.run.app`n" -ForegroundColor Cyan
    }

    Write-Host "🔍 Commandes utiles:" -ForegroundColor Yellow
    Write-Host "  • Logs temps réel:" -ForegroundColor White
    Write-Host "    gcloud run services logs read $SERVICE_NAME --region=$REGION --project=$PROJECT_ID --tail" -ForegroundColor Gray
    Write-Host "  • Dashboard métriques:" -ForegroundColor White
    Write-Host "    https://console.cloud.google.com/run/detail/$REGION/$SERVICE_NAME/metrics?project=$PROJECT_ID`n" -ForegroundColor Gray

} else {
    Write-Host "`n❌ Erreur lors de la mise à jour du trafic" -ForegroundColor Red
    Write-Host "   Vérifier les logs et réessayer`n" -ForegroundColor Yellow
    exit 1
}

Write-Host "════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "✅ Script terminé" -ForegroundColor Green
Write-Host "════════════════════════════════════════════════════════════`n" -ForegroundColor Cyan
