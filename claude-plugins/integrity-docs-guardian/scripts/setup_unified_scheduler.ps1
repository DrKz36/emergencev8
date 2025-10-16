# ============================================================================
# SETUP UNIFIED SCHEDULER - Configuration de la tâche planifiée Phase 3
# ============================================================================
# Ce script configure une tâche planifiée Windows pour exécuter
# le unified_guardian_scheduler.ps1 de manière périodique
# ============================================================================

param(
    [switch]$Force,
    [int]$IntervalMinutes = 60
)

Write-Host "================================================================" -ForegroundColor Cyan
Write-Host "⚙️  CONFIGURATION DU UNIFIED GUARDIAN SCHEDULER" -ForegroundColor Cyan
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host ""

# Vérifier les privilèges administrateur
$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "⚠️  Ce script nécessite des privilèges administrateur" -ForegroundColor Yellow
    Write-Host "   Relancer PowerShell en tant qu'administrateur" -ForegroundColor Yellow
    Write-Host ""
    $response = Read-Host "Continuer quand même? (O/N)"
    if ($response -ne "O" -and $response -ne "o") {
        exit 1
    }
}

# Configuration
$repoRoot = "C:\dev\emergenceV8"
if (-not (Test-Path $repoRoot)) {
    Write-Host "❌ Erreur: Dépôt non trouvé à $repoRoot" -ForegroundColor Red
    exit 1
}

$taskName = "EmergenceUnifiedGuardian"
$scriptPath = Join-Path $repoRoot "claude-plugins\integrity-docs-guardian\scripts\unified_guardian_scheduler.ps1"

# Vérifier que le script existe
if (-not (Test-Path $scriptPath)) {
    Write-Host "❌ Erreur: Script non trouvé: $scriptPath" -ForegroundColor Red
    exit 1
}

Write-Host "📋 Configuration:" -ForegroundColor Yellow
Write-Host "   Nom de la tâche: $taskName" -ForegroundColor White
Write-Host "   Script: $scriptPath" -ForegroundColor White
Write-Host "   Intervalle: $IntervalMinutes minutes" -ForegroundColor White
Write-Host "   Dossier de travail: $repoRoot" -ForegroundColor White
Write-Host ""

# Vérifier si la tâche existe déjà
$existingTask = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue

if ($existingTask) {
    Write-Host "ℹ️  La tâche '$taskName' existe déjà" -ForegroundColor Yellow

    if ($Force) {
        Write-Host "   🔄 Suppression de la tâche existante (mode -Force)..." -ForegroundColor Yellow
        Unregister-ScheduledTask -TaskName $taskName -Confirm:$false
        Write-Host "   ✅ Tâche supprimée" -ForegroundColor Green
        $existingTask = $null
    } else {
        Write-Host ""
        $response = Read-Host "   Voulez-vous la recréer? (O/N)"
        if ($response -eq "O" -or $response -eq "o") {
            Unregister-ScheduledTask -TaskName $taskName -Confirm:$false
            Write-Host "   ✅ Tâche supprimée" -ForegroundColor Green
            $existingTask = $null
        } else {
            Write-Host "   ⏭️  Conservation de la tâche existante" -ForegroundColor Yellow
            Write-Host ""
            Write-Host "💡 Pour modifier la tâche, utilisez -Force ou supprimez-la manuellement:" -ForegroundColor Yellow
            Write-Host "   Unregister-ScheduledTask -TaskName '$taskName' -Confirm:`$false" -ForegroundColor Cyan
            Write-Host ""
            exit 0
        }
    }
}

# Créer la tâche planifiée
if (-not $existingTask) {
    Write-Host ""
    Write-Host "🔧 Création de la tâche planifiée..." -ForegroundColor Green

    try {
        # Définir l'action - Exécuter PowerShell en arrière-plan sans fenêtre
        $action = New-ScheduledTaskAction `
            -Execute "powershell.exe" `
            -Argument "-WindowStyle Hidden -NoProfile -ExecutionPolicy Bypass -File `"$scriptPath`"" `
            -WorkingDirectory $repoRoot

        Write-Host "   ✅ Action configurée" -ForegroundColor White

        # Définir les déclencheurs
        # 1. Au démarrage du système
        $triggerStartup = New-ScheduledTaskTrigger -AtStartup

        # 2. Répétition périodique (toutes les X minutes)
        $triggerRepeat = New-ScheduledTaskTrigger `
            -Once `
            -At (Get-Date).AddMinutes(5) `
            -RepetitionInterval (New-TimeSpan -Minutes $IntervalMinutes) `
            -RepetitionDuration ([TimeSpan]::MaxValue)

        Write-Host "   ✅ Déclencheurs configurés:" -ForegroundColor White
        Write-Host "      - Au démarrage du système" -ForegroundColor Gray
        Write-Host "      - Toutes les $IntervalMinutes minutes" -ForegroundColor Gray

        # Définir le principal (utilisateur qui exécute la tâche)
        $principal = New-ScheduledTaskPrincipal `
            -UserId "$env:USERDOMAIN\$env:USERNAME" `
            -LogonType Interactive `
            -RunLevel Limited

        Write-Host "   ✅ Principal configuré: $env:USERDOMAIN\$env:USERNAME" -ForegroundColor White

        # Définir les paramètres
        $settings = New-ScheduledTaskSettingsSet `
            -AllowStartIfOnBatteries `
            -DontStopIfGoingOnBatteries `
            -StartWhenAvailable `
            -RunOnlyIfNetworkAvailable:$false `
            -DontStopOnIdleEnd `
            -ExecutionTimeLimit (New-TimeSpan -Minutes 30) `
            -RestartCount 3 `
            -RestartInterval (New-TimeSpan -Minutes 5)

        Write-Host "   ✅ Paramètres configurés" -ForegroundColor White

        # Créer la tâche
        $task = Register-ScheduledTask `
            -TaskName $taskName `
            -Action $action `
            -Trigger $triggerStartup, $triggerRepeat `
            -Principal $principal `
            -Settings $settings `
            -Description "ÉMERGENCE - Unified Guardian Scheduler (Phase 3) - Orchestration automatique des agents de vérification" `
            -ErrorAction Stop

        Write-Host ""
        Write-Host "   ✅ Tâche planifiée créée avec succès!" -ForegroundColor Green
        Write-Host ""

        # Afficher les détails de la tâche
        $taskInfo = Get-ScheduledTask -TaskName $taskName
        $taskDetails = Get-ScheduledTaskInfo -TaskName $taskName

        Write-Host "📊 Détails de la tâche:" -ForegroundColor Yellow
        Write-Host "   Nom: $($taskInfo.TaskName)" -ForegroundColor White
        Write-Host "   État: $($taskInfo.State)" -ForegroundColor White
        Write-Host "   Prochaine exécution: $($taskDetails.NextRunTime)" -ForegroundColor White
        Write-Host "   Dernière exécution: $($taskDetails.LastRunTime)" -ForegroundColor White
        Write-Host "   Dernier résultat: $($taskDetails.LastTaskResult)" -ForegroundColor White
        Write-Host ""

    } catch {
        Write-Host ""
        Write-Host "❌ Erreur lors de la création de la tâche:" -ForegroundColor Red
        Write-Host "   $($_.Exception.Message)" -ForegroundColor Red
        Write-Host ""
        Write-Host "💡 Solution:" -ForegroundColor Yellow
        Write-Host "   1. Vérifiez que vous avez les droits administrateur" -ForegroundColor White
        Write-Host "   2. Ou créez la tâche manuellement via le Planificateur de tâches" -ForegroundColor White
        Write-Host ""
        Write-Host "   Programme: powershell.exe" -ForegroundColor Gray
        Write-Host "   Arguments: -NoProfile -ExecutionPolicy Bypass -File `"$scriptPath`"" -ForegroundColor Gray
        Write-Host "   Répertoire: $repoRoot" -ForegroundColor Gray
        Write-Host ""
        exit 1
    }
}

# Test optionnel
Write-Host "🧪 Test de la tâche" -ForegroundColor Yellow
$testResponse = Read-Host "Voulez-vous tester la tâche maintenant? (O/N)"

if ($testResponse -eq "O" -or $testResponse -eq "o") {
    Write-Host ""
    Write-Host "   🚀 Démarrage de la tâche..." -ForegroundColor White

    try {
        Start-ScheduledTask -TaskName $taskName
        Write-Host "   ✅ Tâche démarrée" -ForegroundColor Green
        Write-Host ""
        Write-Host "   ⏳ Attente de 5 secondes..." -ForegroundColor White
        Start-Sleep -Seconds 5

        $taskInfo = Get-ScheduledTaskInfo -TaskName $taskName
        Write-Host ""
        Write-Host "   📊 État après exécution:" -ForegroundColor Yellow
        Write-Host "      Dernier résultat: $($taskInfo.LastTaskResult)" -ForegroundColor White
        Write-Host "      Dernière exécution: $($taskInfo.LastRunTime)" -ForegroundColor White
        Write-Host ""

        if ($taskInfo.LastTaskResult -eq 0) {
            Write-Host "   ✅ Test réussi!" -ForegroundColor Green
        } else {
            Write-Host "   ⚠️  Code de résultat: $($taskInfo.LastTaskResult)" -ForegroundColor Yellow
            Write-Host "      Vérifiez les logs pour plus de détails" -ForegroundColor Yellow
        }

        # Afficher le chemin des logs
        $logDir = Join-Path $repoRoot "claude-plugins\integrity-docs-guardian\logs"
        Write-Host ""
        Write-Host "   📁 Logs disponibles dans:" -ForegroundColor Yellow
        Write-Host "      $logDir" -ForegroundColor Gray

    } catch {
        Write-Host "   ❌ Erreur lors du test: $($_.Exception.Message)" -ForegroundColor Red
    }
}

# Résumé final
Write-Host ""
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host "✅ CONFIGURATION TERMINÉE" -ForegroundColor Green
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "🛠️  Commandes utiles:" -ForegroundColor Yellow
Write-Host ""
Write-Host "   # Voir l'état de la tâche" -ForegroundColor Gray
Write-Host "   Get-ScheduledTask -TaskName '$taskName'" -ForegroundColor Cyan
Write-Host ""
Write-Host "   # Démarrer la tâche manuellement" -ForegroundColor Gray
Write-Host "   Start-ScheduledTask -TaskName '$taskName'" -ForegroundColor Cyan
Write-Host ""
Write-Host "   # Arrêter la tâche" -ForegroundColor Gray
Write-Host "   Stop-ScheduledTask -TaskName '$taskName'" -ForegroundColor Cyan
Write-Host ""
Write-Host "   # Désactiver la tâche" -ForegroundColor Gray
Write-Host "   Disable-ScheduledTask -TaskName '$taskName'" -ForegroundColor Cyan
Write-Host ""
Write-Host "   # Activer la tâche" -ForegroundColor Gray
Write-Host "   Enable-ScheduledTask -TaskName '$taskName'" -ForegroundColor Cyan
Write-Host ""
Write-Host "   # Supprimer la tâche" -ForegroundColor Gray
Write-Host "   Unregister-ScheduledTask -TaskName '$taskName' -Confirm:`$false" -ForegroundColor Cyan
Write-Host ""
Write-Host "   # Voir l'historique d'exécution" -ForegroundColor Gray
Write-Host "   Get-ScheduledTaskInfo -TaskName '$taskName'" -ForegroundColor Cyan
Write-Host ""

Write-Host "📁 Fichiers importants:" -ForegroundColor Yellow
Write-Host "   Script: $scriptPath" -ForegroundColor Gray
Write-Host "   Logs: $(Join-Path $repoRoot 'claude-plugins\integrity-docs-guardian\logs')" -ForegroundColor Gray
Write-Host "   Rapports: $(Join-Path $repoRoot 'claude-plugins\integrity-docs-guardian\reports')" -ForegroundColor Gray
Write-Host ""

Write-Host "================================================================" -ForegroundColor Cyan
Write-Host ""
