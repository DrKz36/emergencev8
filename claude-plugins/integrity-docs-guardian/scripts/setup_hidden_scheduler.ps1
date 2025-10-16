# ============================================================================
# SETUP HIDDEN SCHEDULER - Configuration avec execution cachee
# ============================================================================
# Ce script configure une tache planifiee qui s'execute en arriere-plan
# sans afficher de fenetre PowerShell
# ============================================================================

param(
    [switch]$Force,
    [int]$IntervalMinutes = 60
)

Write-Host "================================================================" -ForegroundColor Cyan
Write-Host "CONFIGURATION DU SCHEDULER EN MODE CACHE" -ForegroundColor Cyan
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host ""

# Configuration
$repoRoot = "C:\dev\emergenceV8"
if (-not (Test-Path $repoRoot)) {
    Write-Host "ERREUR: Depot non trouve a $repoRoot" -ForegroundColor Red
    exit 1
}

$taskName = "EmergenceUnifiedGuardian"
$vbsScriptPath = Join-Path $repoRoot "claude-plugins\integrity-docs-guardian\scripts\run_unified_scheduler_hidden.vbs"

# Verifier que le script VBS existe
if (-not (Test-Path $vbsScriptPath)) {
    Write-Host "ERREUR: Script VBS non trouve: $vbsScriptPath" -ForegroundColor Red
    exit 1
}

Write-Host "Configuration:" -ForegroundColor Yellow
Write-Host "  Nom de la tache: $taskName" -ForegroundColor White
Write-Host "  Script VBS: $vbsScriptPath" -ForegroundColor White
Write-Host "  Intervalle: $IntervalMinutes minutes" -ForegroundColor White
Write-Host "  Mode: CACHE (sans fenetre)" -ForegroundColor Green
Write-Host ""

# Verifier si la tache existe deja
$existingTask = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue

if ($existingTask) {
    Write-Host "INFO: La tache '$taskName' existe deja" -ForegroundColor Yellow

    if ($Force) {
        Write-Host "  Suppression de la tache existante (mode -Force)..." -ForegroundColor Yellow
        Unregister-ScheduledTask -TaskName $taskName -Confirm:$false
        Write-Host "  Tache supprimee" -ForegroundColor Green
        $existingTask = $null
    } else {
        Write-Host ""
        Write-Host "La tache existe deja. Utilisez -Force pour la recreer" -ForegroundColor Yellow
        Write-Host "Ou supprimez-la manuellement:" -ForegroundColor Yellow
        Write-Host "  Unregister-ScheduledTask -TaskName '$taskName' -Confirm:`$false" -ForegroundColor Cyan
        Write-Host ""
        exit 0
    }
}

# Creer la tache planifiee
if (-not $existingTask) {
    Write-Host ""
    Write-Host "Creation de la tache planifiee en mode cache..." -ForegroundColor Green

    try {
        # Definir l'action - Executer le script VBS (qui lance PowerShell en cache)
        $action = New-ScheduledTaskAction `
            -Execute "wscript.exe" `
            -Argument "`"$vbsScriptPath`"" `
            -WorkingDirectory $repoRoot

        Write-Host "  Action configuree (via VBScript)" -ForegroundColor White

        # Definir les declencheurs
        # 1. Au demarrage du systeme
        $triggerStartup = New-ScheduledTaskTrigger -AtStartup

        # 2. Repetition periodique (toutes les X minutes)
        $triggerRepeat = New-ScheduledTaskTrigger `
            -Once `
            -At (Get-Date).AddMinutes(5) `
            -RepetitionInterval (New-TimeSpan -Minutes $IntervalMinutes)

        Write-Host "  Declencheurs configures:" -ForegroundColor White
        Write-Host "    - Au demarrage du systeme" -ForegroundColor Gray
        Write-Host "    - Toutes les $IntervalMinutes minutes" -ForegroundColor Gray

        # Definir le principal (utilisateur qui execute la tache)
        $principal = New-ScheduledTaskPrincipal `
            -UserId "$env:USERNAME" `
            -LogonType InteractiveOrPassword `
            -RunLevel Limited

        Write-Host "  Principal configure: $env:USERNAME" -ForegroundColor White

        # Definir les parametres
        $settings = New-ScheduledTaskSettingsSet `
            -AllowStartIfOnBatteries `
            -DontStopIfGoingOnBatteries `
            -StartWhenAvailable `
            -RunOnlyIfNetworkAvailable:$false `
            -DontStopOnIdleEnd `
            -ExecutionTimeLimit (New-TimeSpan -Minutes 30) `
            -RestartCount 3 `
            -RestartInterval (New-TimeSpan -Minutes 5) `
            -Hidden

        Write-Host "  Parametres configures (mode cache)" -ForegroundColor White

        # Creer la tache
        $task = Register-ScheduledTask `
            -TaskName $taskName `
            -Action $action `
            -Trigger $triggerStartup, $triggerRepeat `
            -Principal $principal `
            -Settings $settings `
            -Description "EMERGENCE - Unified Guardian Scheduler (Hidden) - Orchestration automatique sans fenetre" `
            -ErrorAction Stop

        Write-Host ""
        Write-Host "  Tache planifiee creee avec succes en mode CACHE!" -ForegroundColor Green
        Write-Host ""

        # Afficher les details de la tache
        $taskInfo = Get-ScheduledTask -TaskName $taskName
        $taskDetails = Get-ScheduledTaskInfo -TaskName $taskName

        Write-Host "Details de la tache:" -ForegroundColor Yellow
        Write-Host "  Nom: $($taskInfo.TaskName)" -ForegroundColor White
        Write-Host "  Etat: $($taskInfo.State)" -ForegroundColor White
        Write-Host "  Mode: CACHE (sans fenetre)" -ForegroundColor Green
        Write-Host "  Prochaine execution: $($taskDetails.NextRunTime)" -ForegroundColor White
        Write-Host "  Derniere execution: $($taskDetails.LastRunTime)" -ForegroundColor White
        Write-Host "  Dernier resultat: $($taskDetails.LastTaskResult)" -ForegroundColor White
        Write-Host ""

    } catch {
        Write-Host ""
        Write-Host "ERREUR lors de la creation de la tache:" -ForegroundColor Red
        Write-Host "  $($_.Exception.Message)" -ForegroundColor Red
        Write-Host ""
        Write-Host "Solution:" -ForegroundColor Yellow
        Write-Host "  1. Verifiez que vous avez les droits administrateur" -ForegroundColor White
        Write-Host "  2. Ou creez la tache manuellement via le Planificateur de taches" -ForegroundColor White
        Write-Host ""
        Write-Host "  Programme: wscript.exe" -ForegroundColor Gray
        Write-Host "  Arguments: `"$vbsScriptPath`"" -ForegroundColor Gray
        Write-Host "  Repertoire: $repoRoot" -ForegroundColor Gray
        Write-Host ""
        exit 1
    }
}

# Test manuel
Write-Host "Pour tester la tache maintenant (execution cachee):" -ForegroundColor Yellow
Write-Host "  Start-ScheduledTask -TaskName '$taskName'" -ForegroundColor Cyan
Write-Host ""
Write-Host "OU directement via VBScript:" -ForegroundColor Yellow
Write-Host "  wscript.exe `"$vbsScriptPath`"" -ForegroundColor Cyan
Write-Host ""

# Resume final
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host "CONFIGURATION TERMINEE - MODE CACHE ACTIVE" -ForegroundColor Green
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "IMPORTANT: Aucune fenetre PowerShell ne s'affichera!" -ForegroundColor Green
Write-Host "Les logs seront disponibles dans:" -ForegroundColor Yellow
Write-Host "  $(Join-Path $repoRoot 'claude-plugins\integrity-docs-guardian\logs')" -ForegroundColor Cyan
Write-Host ""

Write-Host "Commandes utiles:" -ForegroundColor Yellow
Write-Host ""
Write-Host "  # Voir l'etat de la tache" -ForegroundColor Gray
Write-Host "  Get-ScheduledTask -TaskName '$taskName'" -ForegroundColor Cyan
Write-Host ""
Write-Host "  # Demarrer la tache manuellement (cache)" -ForegroundColor Gray
Write-Host "  Start-ScheduledTask -TaskName '$taskName'" -ForegroundColor Cyan
Write-Host ""
Write-Host "  # Voir les logs en temps reel" -ForegroundColor Gray
Write-Host "  Get-Content '$(Join-Path $repoRoot 'claude-plugins\integrity-docs-guardian\logs\unified_scheduler_*.log')' -Wait -Tail 20" -ForegroundColor Cyan
Write-Host ""

Write-Host "================================================================" -ForegroundColor Cyan
Write-Host ""
