# Script de configuration automatique de la tâche planifiée Windows
# Pour ÉMERGENCE - Orchestration automatique des agents

param(
    [int]$IntervalMinutes = 60,
    [switch]$Force
)

Write-Host "================================================================" -ForegroundColor Cyan
Write-Host "CONFIGURATION TASK SCHEDULER - ORCHESTRATION AUTOMATIQUE" -ForegroundColor Cyan
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host ""

$repoRoot = "C:\dev\emergenceV8"
if (-not (Test-Path $repoRoot)) {
    Write-Host "ERREUR: Depot non trouve a $repoRoot" -ForegroundColor Red
    exit 1
}

Set-Location $repoRoot

# Configuration
$taskName = "EMERGENCE_AutoOrchestration"
$pythonExe = "$repoRoot\.venv\Scripts\python.exe"
$schedulerScript = "$repoRoot\claude-plugins\integrity-docs-guardian\scripts\scheduler.py"

# Vérifier que Python et le script existent
if (-not (Test-Path $pythonExe)) {
    Write-Host "ERREUR: Python non trouve: $pythonExe" -ForegroundColor Red
    Write-Host "Essai avec python global..." -ForegroundColor Yellow
    $pythonExe = (Get-Command python -ErrorAction SilentlyContinue).Source
    if (-not $pythonExe) {
        Write-Host "ERREUR: Python introuvable" -ForegroundColor Red
        exit 1
    }
}

if (-not (Test-Path $schedulerScript)) {
    Write-Host "ERREUR: Script scheduler non trouve: $schedulerScript" -ForegroundColor Red
    exit 1
}

Write-Host "Configuration:" -ForegroundColor Yellow
Write-Host "  - Python: $pythonExe" -ForegroundColor Gray
Write-Host "  - Script: $schedulerScript" -ForegroundColor Gray
Write-Host "  - Intervalle: $IntervalMinutes minutes" -ForegroundColor Gray
Write-Host ""

# Vérifier si la tâche existe déjà
$existingTask = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue

if ($existingTask -and -not $Force) {
    Write-Host "INFO: La tache '$taskName' existe deja" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Options:" -ForegroundColor Cyan
    Write-Host "  1. Supprimer et recreer" -ForegroundColor White
    Write-Host "  2. Garder l'existante" -ForegroundColor White
    Write-Host "  3. Annuler" -ForegroundColor White
    Write-Host ""
    $choice = Read-Host "Votre choix (1/2/3)"

    switch ($choice) {
        "1" {
            Unregister-ScheduledTask -TaskName $taskName -Confirm:$false
            Write-Host "OK Tache supprimee" -ForegroundColor Green
        }
        "2" {
            Write-Host "OK Conservation de la tache existante" -ForegroundColor Green
            Write-Host ""
            Write-Host "Pour la voir:" -ForegroundColor Cyan
            Write-Host "  Get-ScheduledTask -TaskName '$taskName' | Format-List" -ForegroundColor Gray
            exit 0
        }
        default {
            Write-Host "Operation annulee" -ForegroundColor Yellow
            exit 0
        }
    }
} elseif ($existingTask -and $Force) {
    Unregister-ScheduledTask -TaskName $taskName -Confirm:$false
    Write-Host "OK Tache existante supprimee (mode Force)" -ForegroundColor Green
}

Write-Host ""
Write-Host "Creation de la tache planifiee..." -ForegroundColor Yellow
Write-Host ""

try {
    # Définir l'action
    $actionArgs = @(
        "claude-plugins\integrity-docs-guardian\scripts\scheduler.py"
    )

    $action = New-ScheduledTaskAction `
        -Execute $pythonExe `
        -Argument ($actionArgs -join " ") `
        -WorkingDirectory $repoRoot

    # Définir le déclencheur (répétition toutes les X minutes)
    # Note: Durée de répétition fixée à 10 ans (limitation Windows)
    $trigger = New-ScheduledTaskTrigger `
        -Once `
        -At (Get-Date).AddMinutes(2) `
        -RepetitionInterval (New-TimeSpan -Minutes $IntervalMinutes)

    # Définir les paramètres
    $settings = New-ScheduledTaskSettingsSet `
        -AllowStartIfOnBatteries `
        -DontStopIfGoingOnBatteries `
        -StartWhenAvailable `
        -RunOnlyIfNetworkAvailable:$false `
        -DontStopOnIdleEnd `
        -ExecutionTimeLimit (New-TimeSpan -Hours 1) `
        -RestartCount 3 `
        -RestartInterval (New-TimeSpan -Minutes 10)

    # Définir le principal (utilisateur courant, privilèges les plus élevés)
    $principal = New-ScheduledTaskPrincipal `
        -UserId "$env:USERDOMAIN\$env:USERNAME" `
        -LogonType Interactive `
        -RunLevel Highest

    # Enregistrer la tâche
    $task = Register-ScheduledTask `
        -TaskName $taskName `
        -Action $action `
        -Trigger $trigger `
        -Settings $settings `
        -Principal $principal `
        -Description "EMERGENCE - Orchestration automatique des agents de verification (toutes les $IntervalMinutes minutes)" `
        -ErrorAction Stop

    # Modifier le trigger pour ajouter une durée indéfinie
    $task = Get-ScheduledTask -TaskName $taskName
    $task.Triggers[0].Repetition.Duration = "P10000D" # ~27 ans
    $task | Set-ScheduledTask -ErrorAction SilentlyContinue | Out-Null

    Write-Host "================================================================" -ForegroundColor Green
    Write-Host "TACHE PLANIFIEE CREEE AVEC SUCCES" -ForegroundColor Green
    Write-Host "================================================================" -ForegroundColor Green
    Write-Host ""

    Write-Host "Details de la tache:" -ForegroundColor Yellow
    Write-Host "  Nom: $taskName" -ForegroundColor White
    Write-Host "  Frequence: Toutes les $IntervalMinutes minutes" -ForegroundColor White
    Write-Host "  Premiere execution: Dans 2 minutes" -ForegroundColor White
    Write-Host "  État: $($task.State)" -ForegroundColor White
    Write-Host ""

    Write-Host "Commandes utiles:" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "  # Voir l'etat de la tache" -ForegroundColor Gray
    Write-Host "  Get-ScheduledTask -TaskName '$taskName'" -ForegroundColor White
    Write-Host ""
    Write-Host "  # Executer la tache manuellement maintenant" -ForegroundColor Gray
    Write-Host "  Start-ScheduledTask -TaskName '$taskName'" -ForegroundColor White
    Write-Host ""
    Write-Host "  # Voir l'historique d'execution" -ForegroundColor Gray
    Write-Host "  Get-ScheduledTaskInfo -TaskName '$taskName'" -ForegroundColor White
    Write-Host ""
    Write-Host "  # Voir les logs du scheduler" -ForegroundColor Gray
    Write-Host "  Get-Content claude-plugins\integrity-docs-guardian\logs\scheduler.log -Tail 50" -ForegroundColor White
    Write-Host ""
    Write-Host "  # Desactiver la tache" -ForegroundColor Gray
    Write-Host "  Disable-ScheduledTask -TaskName '$taskName'" -ForegroundColor White
    Write-Host ""
    Write-Host "  # Reactiver la tache" -ForegroundColor Gray
    Write-Host "  Enable-ScheduledTask -TaskName '$taskName'" -ForegroundColor White
    Write-Host ""
    Write-Host "  # Supprimer la tache" -ForegroundColor Gray
    Write-Host "  Unregister-ScheduledTask -TaskName '$taskName' -Confirm:`$false" -ForegroundColor White
    Write-Host ""

    # Test de la tâche
    Write-Host "Voulez-vous executer la tache maintenant pour la tester? (O/N)" -ForegroundColor Cyan
    $testNow = Read-Host

    if ($testNow -eq "O" -or $testNow -eq "o") {
        Write-Host ""
        Write-Host "Execution de la tache..." -ForegroundColor Yellow
        Start-ScheduledTask -TaskName $taskName
        Start-Sleep -Seconds 3

        $taskInfo = Get-ScheduledTaskInfo -TaskName $taskName
        Write-Host "OK Tache executee" -ForegroundColor Green
        Write-Host "  Derniere execution: $($taskInfo.LastRunTime)" -ForegroundColor Gray
        Write-Host "  Resultat: $($taskInfo.LastTaskResult)" -ForegroundColor Gray
        Write-Host ""
        Write-Host "Verifiez les logs:" -ForegroundColor Cyan
        Write-Host "  Get-Content claude-plugins\integrity-docs-guardian\logs\scheduler.log -Tail 20" -ForegroundColor Gray
    }

    Write-Host ""
    Write-Host "================================================================" -ForegroundColor Green
    Write-Host "ORCHESTRATION AUTOMATIQUE CONFIGUREE" -ForegroundColor Green
    Write-Host "================================================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "Votre systeme va maintenant:" -ForegroundColor Yellow
    Write-Host "  1. Executer les agents toutes les $IntervalMinutes minutes" -ForegroundColor White
    Write-Host "  2. Executer les agents apres chaque commit Git" -ForegroundColor White
    Write-Host "  3. Mettre a jour la documentation automatiquement" -ForegroundColor White
    Write-Host "  4. Generer des rapports de sante de l'application" -ForegroundColor White
    Write-Host ""
    Write-Host "Systeme 100% autonome active!" -ForegroundColor Green
    Write-Host ""

    exit 0

} catch {
    Write-Host ""
    Write-Host "================================================================" -ForegroundColor Red
    Write-Host "ERREUR LORS DE LA CREATION DE LA TACHE" -ForegroundColor Red
    Write-Host "================================================================" -ForegroundColor Red
    Write-Host ""
    Write-Host "Message d'erreur:" -ForegroundColor Yellow
    Write-Host $_.Exception.Message -ForegroundColor Red
    Write-Host ""
    Write-Host "Solutions possibles:" -ForegroundColor Cyan
    Write-Host "  1. Executez PowerShell en tant qu'administrateur" -ForegroundColor White
    Write-Host "  2. Verifiez que le planificateur de taches est active" -ForegroundColor White
    Write-Host "  3. Creez la tache manuellement (voir GUIDE_TASK_SCHEDULER.md)" -ForegroundColor White
    Write-Host ""
    exit 1
}
