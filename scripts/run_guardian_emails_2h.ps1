# Script pour envoyer les rapports Guardian par email toutes les 2h
# Génère des rapports frais à chaque exécution

param(
    [int]$DurationHours = 24
)

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  GUARDIAN EMAILS AUTOMATIQUES - TOUTES LES 2H" -ForegroundColor Cyan
Write-Host "============================================================`n" -ForegroundColor Cyan

Write-Host "Configuration:" -ForegroundColor Yellow
Write-Host "  - Fréquence: Toutes les 2 heures" -ForegroundColor White
Write-Host "  - Durée: $DurationHours heures" -ForegroundColor White
Write-Host "  - Email: gonzalefernando@gmail.com" -ForegroundColor White
Write-Host "  - Type: Rapport Guardian complet (données fraîches)`n" -ForegroundColor White

$iterations = [math]::Floor($DurationHours / 2)
$current = 0

while ($current -lt $iterations) {
    $current++
    $timestamp = Get-Date -Format "dd/MM/yyyy HH:mm:ss"

    Write-Host "`n[$current/$iterations] Génération et envoi rapport Guardian - $timestamp" -ForegroundColor Cyan
    Write-Host ("=" * 60) -ForegroundColor DarkGray

    # Lancer le script Python Guardian
    python scripts/guardian_email_report.py

    if ($LASTEXITCODE -eq 0) {
        Write-Host "`n  Email Guardian envoyé avec succès!" -ForegroundColor Green
    } else {
        Write-Host "`n  Erreur lors de la génération/envoi" -ForegroundColor Red
    }

    # Attendre 2h sauf si c'est la dernière itération
    if ($current -lt $iterations) {
        $nextTime = (Get-Date).AddHours(2).ToString('HH:mm')
        Write-Host "`nProchaine exécution dans 2h (à $nextTime)..." -ForegroundColor Yellow
        Write-Host "Appuyez sur Ctrl+C pour arrêter`n" -ForegroundColor DarkGray
        Start-Sleep -Seconds 7200
    }
}

Write-Host "`n============================================================" -ForegroundColor Cyan
Write-Host "  FIN - $current rapports Guardian envoyés" -ForegroundColor Green
Write-Host "============================================================`n" -ForegroundColor Cyan
