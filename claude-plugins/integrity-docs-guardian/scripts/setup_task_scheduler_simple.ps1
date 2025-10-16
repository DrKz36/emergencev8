# Script simplifié de configuration de la tâche planifiée (sans privilèges admin)
# Pour ÉMERGENCE - Orchestration automatique

param([int]$IntervalMinutes = 60)

Write-Host "================================================================" -ForegroundColor Cyan
Write-Host "CONFIGURATION TASK SCHEDULER (Mode Simple)" -ForegroundColor Cyan
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host ""

$taskName = "EMERGENCE_AutoOrchestration"
$pythonExe = "C:\dev\emergenceV8\.venv\Scripts\python.exe"
$scriptPath = "C:\dev\emergenceV8\claude-plugins\integrity-docs-guardian\scripts\scheduler.py"

# Vérifier si la tâche existe
$existingTask = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue

if ($existingTask) {
    Write-Host "INFO: Tache '$taskName' existe deja" -ForegroundColor Yellow
    Write-Host "État: $($existingTask.State)" -ForegroundColor Gray
    Write-Host ""
    Write-Host "Pour la supprimer:" -ForegroundColor Cyan
    Write-Host "  Unregister-ScheduledTask -TaskName '$taskName' -Confirm:`$false" -ForegroundColor Gray
    exit 0
}

Write-Host "Creation de la tache..." -ForegroundColor Yellow

try {
    # Créer l'action
    $action = New-ScheduledTaskAction `
        -Execute $pythonExe `
        -Argument $scriptPath `
        -WorkingDirectory "C:\dev\emergenceV8"

    # Créer le trigger (toutes les heures)
    $trigger = New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(2) -RepetitionInterval (New-TimeSpan -Minutes $IntervalMinutes)

    # Paramètres
    $settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries

    # Créer sans privilèges élevés
    Register-ScheduledTask `
        -TaskName $taskName `
        -Action $action `
        -Trigger $trigger `
        -Settings $settings `
        -Description "EMERGENCE - Orchestration automatique (toutes les $IntervalMinutes min)" | Out-Null

    Write-Host "OK Tache creee avec succes!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Details:" -ForegroundColor Yellow
    Write-Host "  Nom: $taskName" -ForegroundColor White
    Write-Host "  Frequence: Toutes les $IntervalMinutes minutes" -ForegroundColor White
    Write-Host "  Premiere execution: Dans 2 minutes" -ForegroundColor White
    Write-Host ""
    Write-Host "Tester maintenant:" -ForegroundColor Cyan
    Write-Host "  Start-ScheduledTask -TaskName '$taskName'" -ForegroundColor Gray
    Write-Host ""

} catch {
    Write-Host "ERREUR: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host ""
    Write-Host "Solution: Utilisez la methode manuelle (GUIDE_TASK_SCHEDULER.md)" -ForegroundColor Yellow
    exit 1
}
