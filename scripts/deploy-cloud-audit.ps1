# Script de déploiement du Cloud Audit Job + Cloud Scheduler
# ÉMERGENCE V8 - Automatisation audit 3x/jour

param(
    [string]$ProjectId = "emergence-app-prod",
    [string]$Region = "europe-west1",
    [string]$ServiceAccount = "emergence-app@emergence-app-prod.iam.gserviceaccount.com"
)

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  DÉPLOIEMENT CLOUD AUDIT JOB + SCHEDULER" -ForegroundColor Cyan
Write-Host "============================================================`n" -ForegroundColor Cyan

# 1. Build de l'image Docker
Write-Host "[1/5] Build de l'image Docker..." -ForegroundColor Yellow
$ImageName = "europe-west1-docker.pkg.dev/$ProjectId/emergence/cloud-audit-job"
$ImageTag = "latest"

docker build -f Dockerfile.audit -t "${ImageName}:${ImageTag}" .

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Erreur lors du build Docker" -ForegroundColor Red
    exit 1
}

Write-Host "✅ Build Docker réussi`n" -ForegroundColor Green

# 2. Push de l'image vers Artifact Registry
Write-Host "[2/5] Push vers Artifact Registry..." -ForegroundColor Yellow

# Configurer Docker pour Artifact Registry
gcloud auth configure-docker europe-west1-docker.pkg.dev --quiet

docker push "${ImageName}:${ImageTag}"

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Erreur lors du push Docker" -ForegroundColor Red
    exit 1
}

Write-Host "✅ Push Docker réussi`n" -ForegroundColor Green

# 3. Déployer le Cloud Run Job
Write-Host "[3/5] Déploiement Cloud Run Job..." -ForegroundColor Yellow

gcloud run jobs deploy cloud-audit-job `
    --image="${ImageName}:${ImageTag}" `
    --region=$Region `
    --project=$ProjectId `
    --service-account=$ServiceAccount `
    --max-retries=2 `
    --task-timeout=10m `
    --set-env-vars="ADMIN_EMAIL=gonzalefernando@gmail.com,SERVICE_URL=https://emergence-app-574876800592.europe-west1.run.app" `
    --set-secrets="SMTP_PASSWORD=smtp-password:latest,OPENAI_API_KEY=openai-api-key:latest" `
    --memory=512Mi `
    --cpu=1

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Erreur lors du déploiement Cloud Run Job" -ForegroundColor Red
    exit 1
}

Write-Host "✅ Cloud Run Job déployé`n" -ForegroundColor Green

# 4. Créer Cloud Scheduler (3x/jour)
Write-Host "[4/5] Configuration Cloud Scheduler (3x/jour)..." -ForegroundColor Yellow

# Horaires: 08:00, 14:00, 20:00 (Europe/Zurich)
$Schedules = @(
    @{ Name = "cloud-audit-morning"; Cron = "0 8 * * *"; Description = "Audit matinal (08:00)" },
    @{ Name = "cloud-audit-afternoon"; Cron = "0 14 * * *"; Description = "Audit après-midi (14:00)" },
    @{ Name = "cloud-audit-evening"; Cron = "0 20 * * *"; Description = "Audit soirée (20:00)" }
)

foreach ($Schedule in $Schedules) {
    Write-Host "  Création scheduler: $($Schedule.Description)..." -ForegroundColor Cyan

    # Supprimer l'existant si présent
    gcloud scheduler jobs delete $Schedule.Name `
        --location=$Region `
        --project=$ProjectId `
        --quiet 2>$null

    # Créer le nouveau scheduler
    gcloud scheduler jobs create http $Schedule.Name `
        --location=$Region `
        --project=$ProjectId `
        --schedule="$($Schedule.Cron)" `
        --time-zone="Europe/Zurich" `
        --uri="https://$Region-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/$ProjectId/jobs/cloud-audit-job:run" `
        --http-method=POST `
        --oauth-service-account-email=$ServiceAccount `
        --description="$($Schedule.Description)"

    if ($LASTEXITCODE -eq 0) {
        Write-Host "  ✅ $($Schedule.Name) créé" -ForegroundColor Green
    } else {
        Write-Host "  ❌ Erreur création $($Schedule.Name)" -ForegroundColor Red
    }
}

Write-Host "`n✅ Cloud Scheduler configuré (3 jobs)`n" -ForegroundColor Green

# 5. Test manuel du job
Write-Host "[5/5] Test manuel du Cloud Audit Job..." -ForegroundColor Yellow

$TestExec = Read-Host "Voulez-vous lancer un test maintenant? (o/n)"

if ($TestExec -eq "o") {
    Write-Host "  Lancement du job..." -ForegroundColor Cyan

    gcloud run jobs execute cloud-audit-job `
        --region=$Region `
        --project=$ProjectId `
        --wait

    if ($LASTEXITCODE -eq 0) {
        Write-Host "  ✅ Test réussi - vérifiez votre email!" -ForegroundColor Green
    } else {
        Write-Host "  ❌ Test échoué" -ForegroundColor Red
    }
} else {
    Write-Host "  Test ignoré" -ForegroundColor Yellow
}

Write-Host "`n============================================================" -ForegroundColor Cyan
Write-Host "  ✅ DÉPLOIEMENT TERMINÉ" -ForegroundColor Green
Write-Host "============================================================`n" -ForegroundColor Cyan

Write-Host "📊 Résumé:" -ForegroundColor Yellow
Write-Host "  - Cloud Run Job: cloud-audit-job" -ForegroundColor White
Write-Host "  - Image: $ImageName:$ImageTag" -ForegroundColor White
Write-Host "  - Région: $Region" -ForegroundColor White
Write-Host "  - Email: gonzalefernando@gmail.com" -ForegroundColor White
Write-Host "  - Fréquence: 3x/jour (08:00, 14:00, 20:00 CET)" -ForegroundColor White

Write-Host "`n📧 Prochains rapports automatiques:" -ForegroundColor Yellow
Write-Host "  - Matin: 08:00 (Europe/Zurich)" -ForegroundColor White
Write-Host "  - Après-midi: 14:00 (Europe/Zurich)" -ForegroundColor White
Write-Host "  - Soir: 20:00 (Europe/Zurich)" -ForegroundColor White

Write-Host "`n🔗 Liens utiles:" -ForegroundColor Yellow
Write-Host "  - Cloud Run Jobs: https://console.cloud.google.com/run/jobs?project=$ProjectId" -ForegroundColor Cyan
Write-Host "  - Cloud Scheduler: https://console.cloud.google.com/cloudscheduler?project=$ProjectId" -ForegroundColor Cyan
Write-Host "  - Logs: https://console.cloud.google.com/logs/query?project=$ProjectId" -ForegroundColor Cyan

Write-Host "`n✅ Ton PC n'a plus besoin d'être allumé - tout tourne dans le cloud! 🚀`n" -ForegroundColor Green
