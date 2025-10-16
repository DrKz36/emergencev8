# ============================================================================
# SETUP UNIFIED SCHEDULER - Configuration de la tache planifiee Phase 3
# ============================================================================
# Ce script configure une tache planifiee Windows pour executer
# le unified_guardian_scheduler.ps1 de maniere periodique
# ============================================================================

param(
    [switch]$Force,
    [int]$IntervalMinutes = 60
)

Write-Host "================================================================" -ForegroundColor Cyan
Write-Host "CONFIGURATION DU UNIFIED GUARDIAN SCHEDULER" -ForegroundColor Cyan
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host ""

# Configuration
$repoRoot = "C:\dev\emergenceV8"
if (-not (Test-Path $repoRoot)) {
    Write-Host "ERREUR: Depot non trouve a $repoRoot" -ForegroundColor Red
    exit 1
}

$taskName = "EmergenceUnifiedGuardian"
$scriptPath = Join-Path $repoRoot "claude-plugins\integrity-docs-guardian\scripts\unified_guardian_scheduler.ps1"

# Verifier que le script existe
if (-not (Test-Path $scriptPath)) {
    Write-Host "ERREUR: Script non trouve: $scriptPath" -ForegroundColor Red
    exit 1
}

Write-Host "Configuration:" -ForegroundColor Yellow
Write-Host "  Nom de la tache: $taskName" -ForegroundColor White
Write-Host "  Script: $scriptPath" -ForegroundColor White
Write-Host "  Intervalle: $IntervalMinutes minutes" -ForegroundColor White
Write-Host "  Dossier de travail: $repoRoot" -ForegroundColor White
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
    Write-Host "Creation de la tache planifiee..." -ForegroundColor Green

    try {
        # Definir l'action - Executer PowerShell avec le script
        $action = New-ScheduledTaskAction `
            -Execute "powershell.exe" `
            -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$scriptPath`"" `
            -WorkingDirectory $repoRoot

        Write-Host "  Action configuree" -ForegroundColor White

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

        Write-Host "  Principal configure: $env:USERDOMAIN\$env:USERNAME" -ForegroundColor White

        # Definir les parametres
        $settings = New-ScheduledTaskSettingsSet `
            -AllowStartIfOnBatteries `
            -DontStopIfGoingOnBatteries `
            -StartWhenAvailable `
            -RunOnlyIfNetworkAvailable:$false `
            -DontStopOnIdleEnd `
            -ExecutionTimeLimit (New-TimeSpan -Minutes 30) `
            -RestartCount 3 `
            -RestartInterval (New-TimeSpan -Minutes 5)

        Write-Host "  Parametres configures" -ForegroundColor White

        # Creer la tache
        $task = Register-ScheduledTask `
            -TaskName $taskName `
            -Action $action `
            -Trigger $triggerStartup, $triggerRepeat `
            -Principal $principal `
            -Settings $settings `
            -Description "EMERGENCE - Unified Guardian Scheduler (Phase 3) - Orchestration automatique des agents de verification" `
            -ErrorAction Stop

        Write-Host ""
        Write-Host "  Tache planifiee creee avec succes!" -ForegroundColor Green
        Write-Host ""

        # Afficher les details de la tache
        $taskInfo = Get-ScheduledTask -TaskName $taskName
        $taskDetails = Get-ScheduledTaskInfo -TaskName $taskName

        Write-Host "Details de la tache:" -ForegroundColor Yellow
        Write-Host "  Nom: $($taskInfo.TaskName)" -ForegroundColor White
        Write-Host "  Etat: $($taskInfo.State)" -ForegroundColor White
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
        Write-Host "  Programme: powershell.exe" -ForegroundColor Gray
        Write-Host "  Arguments: -NoProfile -ExecutionPolicy Bypass -File `"$scriptPath`"" -ForegroundColor Gray
        Write-Host "  Repertoire: $repoRoot" -ForegroundColor Gray
        Write-Host ""
        exit 1
    }
}

# Test manuel
Write-Host "Pour tester la tache maintenant:" -ForegroundColor Yellow
Write-Host "  Start-ScheduledTask -TaskName '$taskName'" -ForegroundColor Cyan
Write-Host ""

# Resume final
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host "CONFIGURATION TERMINEE" -ForegroundColor Green
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "Commandes utiles:" -ForegroundColor Yellow
Write-Host ""
Write-Host "  # Voir l'etat de la tache" -ForegroundColor Gray
Write-Host "  Get-ScheduledTask -TaskName '$taskName'" -ForegroundColor Cyan
Write-Host ""
Write-Host "  # Demarrer la tache manuellement" -ForegroundColor Gray
Write-Host "  Start-ScheduledTask -TaskName '$taskName'" -ForegroundColor Cyan
Write-Host ""
Write-Host "  # Arreter la tache" -ForegroundColor Gray
Write-Host "  Stop-ScheduledTask -TaskName '$taskName'" -ForegroundColor Cyan
Write-Host ""
Write-Host "  # Desactiver la tache" -ForegroundColor Gray
Write-Host "  Disable-ScheduledTask -TaskName '$taskName'" -ForegroundColor Cyan
Write-Host ""
Write-Host "  # Supprimer la tache" -ForegroundColor Gray
Write-Host "  Unregister-ScheduledTask -TaskName '$taskName' -Confirm:`$false" -ForegroundColor Cyan
Write-Host ""
Write-Host "  # Voir l'historique d'execution" -ForegroundColor Gray
Write-Host "  Get-ScheduledTaskInfo -TaskName '$taskName'" -ForegroundColor Cyan
Write-Host ""

Write-Host "Fichiers importants:" -ForegroundColor Yellow
Write-Host "  Script: $scriptPath" -ForegroundColor Gray
Write-Host "  Logs: $(Join-Path $repoRoot 'claude-plugins\integrity-docs-guardian\logs')" -ForegroundColor Gray
Write-Host "  Rapports: $(Join-Path $repoRoot 'claude-plugins\integrity-docs-guardian\reports')" -ForegroundColor Gray
Write-Host ""

Write-Host "================================================================" -ForegroundColor Cyan
Write-Host ""
