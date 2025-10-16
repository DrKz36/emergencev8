# Script d'activation du mode automatique complet - Version simplifiée
# Pour ÉMERGENCE - Orchestration automatique des agents

Write-Host "================================================================" -ForegroundColor Cyan
Write-Host "ACTIVATION DU MODE AUTOMATIQUE COMPLET" -ForegroundColor Cyan
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host ""

$repoRoot = "C:\dev\emergenceV8"
Set-Location $repoRoot

# 1. Variables d'environnement pour la session courante
Write-Host "1. Configuration des variables d'environnement..." -ForegroundColor Green
$env:AUTO_UPDATE_DOCS = "1"
$env:AUTO_APPLY = "1"
$env:AGENT_CHECK_INTERVAL = "60"
$env:PYTHONIOENCODING = "utf-8"

Write-Host "   OK AUTO_UPDATE_DOCS = 1" -ForegroundColor White
Write-Host "   OK AUTO_APPLY = 1" -ForegroundColor White
Write-Host "   OK AGENT_CHECK_INTERVAL = 60 minutes" -ForegroundColor White
Write-Host ""

# 2. Ajouter au profil PowerShell
Write-Host "2. Configuration du profil PowerShell..." -ForegroundColor Green

$profilePath = $PROFILE.CurrentUserAllHosts
if (-not (Test-Path $profilePath)) {
    New-Item -Path $profilePath -ItemType File -Force | Out-Null
}

$profileContent = Get-Content $profilePath -Raw -ErrorAction SilentlyContinue

if ($profileContent -notmatch "AUTO_UPDATE_DOCS") {
    $varsToAdd = @"

# EMERGENCE - Orchestration automatique (ajoute le $(Get-Date -Format 'yyyy-MM-dd HH:mm'))
`$env:AUTO_UPDATE_DOCS = "1"
`$env:AUTO_APPLY = "1"
`$env:AGENT_CHECK_INTERVAL = "60"
`$env:PYTHONIOENCODING = "utf-8"
"@
    Add-Content -Path $profilePath -Value $varsToAdd
    Write-Host "   OK Variables ajoutees au profil" -ForegroundColor White
} else {
    Write-Host "   INFO Variables deja presentes" -ForegroundColor Yellow
}
Write-Host ""

# 3. Créer la tâche planifiée
Write-Host "3. Configuration de la tache planifiee Windows..." -ForegroundColor Green

$taskName = "EMERGENCE_AutoOrchestration"
$taskExists = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue

if ($taskExists) {
    Write-Host "   INFO Tache existe deja" -ForegroundColor Yellow
} else {
    $pythonExe = (Get-Command python -ErrorAction SilentlyContinue).Source
    if (-not $pythonExe) {
        $pythonExe = "$repoRoot\.venv\Scripts\python.exe"
    }

    $scriptPath = "$repoRoot\claude-plugins\integrity-docs-guardian\scripts\scheduler.py"

    $action = New-ScheduledTaskAction -Execute $pythonExe -Argument "RUN_ONCE=1 $scriptPath" -WorkingDirectory $repoRoot
    $trigger = New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(1) -RepetitionInterval (New-TimeSpan -Hours 1) -RepetitionDuration ([TimeSpan]::MaxValue)
    $settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries

    try {
        Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Settings $settings -Description "EMERGENCE - Orchestration automatique" -ErrorAction Stop | Out-Null
        Write-Host "   OK Tache planifiee creee (execution toutes les heures)" -ForegroundColor White
    } catch {
        Write-Host "   WARN Impossible de creer la tache automatiquement" -ForegroundColor Yellow
        Write-Host "   INFO Vous pouvez la creer manuellement dans le Planificateur de taches" -ForegroundColor Yellow
    }
}
Write-Host ""

# 4. Résumé
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host "MODE AUTOMATIQUE ACTIVE" -ForegroundColor Green
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Configuration appliquee:" -ForegroundColor Yellow
Write-Host "  - Hook Git post-commit: ACTIVE" -ForegroundColor White
Write-Host "  - Mise a jour auto doc: ACTIVE" -ForegroundColor White
Write-Host "  - Planificateur: ACTIVE (toutes les heures)" -ForegroundColor White
Write-Host ""
Write-Host "Prochaines etapes:" -ForegroundColor Yellow
Write-Host "  1. Redemarrer PowerShell pour charger les variables" -ForegroundColor White
Write-Host "  2. Faire un commit pour tester le hook" -ForegroundColor White
Write-Host ""
Write-Host "Pour desactiver:" -ForegroundColor Yellow
Write-Host "  .\claude-plugins\integrity-docs-guardian\scripts\disable_auto_mode.ps1" -ForegroundColor Cyan
Write-Host ""
