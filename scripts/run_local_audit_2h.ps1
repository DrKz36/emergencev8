# Script LOCAL pour tester les audits toutes les 2h
# En attendant le déploiement Cloud Run (nécessite permissions GCP)
# Ce script simule le comportement cloud en local

param(
    [int]$DurationHours = 24
)

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  AUDIT LOCAL TOUTES LES 2H - MODE TEST" -ForegroundColor Cyan
Write-Host "============================================================`n" -ForegroundColor Cyan

Write-Host "Configuration:" -ForegroundColor Yellow
Write-Host "  - Fréquence: Toutes les 2 heures" -ForegroundColor White
Write-Host "  - Durée: $DurationHours heures" -ForegroundColor White
Write-Host "  - Email: gonzalefernando@gmail.com" -ForegroundColor White
Write-Host "`n"

$iterations = $DurationHours / 2
$current = 0

while ($current -lt $iterations) {
    $current++
    $timestamp = Get-Date -Format "dd/MM/yyyy HH:mm:ss"

    Write-Host "[$current/$iterations] Envoi audit - $timestamp" -ForegroundColor Cyan

    # Lancer le script Python
    python scripts/test_audit_email.py

    if ($LASTEXITCODE -eq 0) {
        Write-Host "  Email envoyé avec succès`n" -ForegroundColor Green
    } else {
        Write-Host "  Erreur lors de l'envoi`n" -ForegroundColor Red
    }

    # Attendre 2h (7200 secondes) sauf si c'est la dernière itération
    if ($current -lt $iterations) {
        Write-Host "Prochaine exécution dans 2h (à $(Get-Date -Date ((Get-Date).AddHours(2)) -Format 'HH:mm'))...`n" -ForegroundColor Yellow
        Start-Sleep -Seconds 7200
    }
}

Write-Host "`n============================================================" -ForegroundColor Cyan
Write-Host "  FIN DU TEST - $current emails envoyés" -ForegroundColor Green
Write-Host "============================================================`n" -ForegroundColor Cyan
