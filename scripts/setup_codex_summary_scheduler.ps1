# Setup Codex Summary Scheduler - Configure Task Scheduler pour génération auto résumé Codex
# Exécution : powershell -ExecutionPolicy Bypass -File setup_codex_summary_scheduler.ps1

param(
    [switch]$Disable,
    [int]$IntervalHours = 6  # Intervalle par défaut : 6h
)

$ErrorActionPreference = "Stop"

# Vérifier droits admin
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "❌ Ce script nécessite les droits administrateur" -ForegroundColor Red
    Write-Host "   Relancez avec: Run as Administrator" -ForegroundColor Yellow
    exit 1
}

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "SETUP CODEX SUMMARY TASK SCHEDULER" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

$TaskName = "Guardian-Codex-Summary"
$RepoRoot = "C:\dev\emergenceV8"
$ScriptPath = "$RepoRoot\scripts\scheduled_codex_summary.ps1"

# Mode désactivation
if ($Disable) {
    Write-Host "🗑️  Désactivation de la tâche planifiée..." -ForegroundColor Yellow

    try {
        Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
        Write-Host "✅ Tâche '$TaskName' supprimée" -ForegroundColor Green
    } catch {
        Write-Host "⚠️  Tâche '$TaskName' n'existe pas" -ForegroundColor Yellow
    }

    exit 0
}

# Mode activation
Write-Host "📋 Configuration de la tâche planifiée..." -ForegroundColor Yellow
Write-Host "   Nom: $TaskName" -ForegroundColor Gray
Write-Host "   Intervalle: Toutes les $IntervalHours heures" -ForegroundColor Gray
Write-Host "   Script: $ScriptPath" -ForegroundColor Gray
Write-Host ""

# Vérifier que le script existe
if (-not (Test-Path $ScriptPath)) {
    Write-Host "❌ Script non trouvé: $ScriptPath" -ForegroundColor Red
    exit 1
}

# Supprimer ancienne tâche si elle existe
try {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
    Write-Host "♻️  Ancienne tâche supprimée" -ForegroundColor Yellow
} catch {
    # Pas d'ancienne tâche, c'est OK
}

# Créer action
$action = New-ScheduledTaskAction `
    -Execute "powershell.exe" `
    -Argument "-ExecutionPolicy Bypass -WindowStyle Hidden -File `"$ScriptPath`""

# Créer déclencheurs (plusieurs pour couvrir 24h)
$triggers = @()

# Calcul nombre de déclencheurs nécessaires
$numTriggers = [Math]::Floor(24 / $IntervalHours)

for ($i = 0; $i -lt $numTriggers; $i++) {
    $hour = $i * $IntervalHours
    $time = "{0:D2}:00" -f $hour

    $trigger = New-ScheduledTaskTrigger -Daily -At $time
    $triggers += $trigger

    Write-Host "   ⏰ Déclencheur: $time (toutes les 24h)" -ForegroundColor Gray
}

# Créer settings
$settings = New-ScheduledTaskSettings `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -RunOnlyIfNetworkAvailable

# Créer principal (run as SYSTEM ou current user)
$principal = New-ScheduledTaskPrincipal `
    -UserId "$env:USERDOMAIN\$env:USERNAME" `
    -LogonType Interactive `
    -RunLevel Limited

# Enregistrer la tâche
try {
    Register-ScheduledTask `
        -TaskName $TaskName `
        -Action $action `
        -Trigger $triggers `
        -Settings $settings `
        -Principal $principal `
        -Description "Génère automatiquement le résumé Guardian pour Codex GPT (toutes les $IntervalHours heures)" `
        -Force | Out-Null

    Write-Host ""
    Write-Host "✅ Tâche planifiée '$TaskName' créée avec succès!" -ForegroundColor Green
    Write-Host ""

    # Afficher les prochaines exécutions
    Write-Host "📅 Prochaines exécutions:" -ForegroundColor Yellow
    $task = Get-ScheduledTask -TaskName $TaskName
    $taskInfo = Get-ScheduledTaskInfo -TaskName $TaskName

    if ($taskInfo.NextRunTime) {
        Write-Host "   🕒 Prochaine: $($taskInfo.NextRunTime)" -ForegroundColor Gray
    }

    Write-Host ""
    Write-Host "💡 Commandes utiles:" -ForegroundColor Yellow
    Write-Host "   - Lancer maintenant:  Start-ScheduledTask -TaskName '$TaskName'" -ForegroundColor Gray
    Write-Host "   - Voir status:        Get-ScheduledTask -TaskName '$TaskName'" -ForegroundColor Gray
    Write-Host "   - Voir logs:          Get-Content logs\scheduled_codex_summary.log" -ForegroundColor Gray
    Write-Host "   - Désactiver:         .\scripts\setup_codex_summary_scheduler.ps1 -Disable" -ForegroundColor Gray

} catch {
    Write-Host "❌ Erreur création tâche planifiée: $_" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "✅ SETUP TERMINÉ" -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Cyan

exit 0
