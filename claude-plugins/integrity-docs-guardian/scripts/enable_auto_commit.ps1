# ============================================================================
# ENABLE AUTO_COMMIT - Configuration pour les agents Guardian
# ============================================================================
# Ce script active le commit automatique pour les agents guardian
# Les changements détectés par les agents seront automatiquement committés
# sans demander confirmation
# ============================================================================

param(
    [switch]$UserLevel,
    [switch]$Disable
)

$ColorSuccess = "Green"
$ColorWarning = "Yellow"
$ColorError = "Red"
$ColorInfo = "Cyan"

Write-Host "============================================================================" -ForegroundColor $ColorInfo
Write-Host "  CONFIGURATION AUTO_COMMIT - Agents Guardian" -ForegroundColor $ColorInfo
Write-Host "============================================================================" -ForegroundColor $ColorInfo
Write-Host ""

# Déterminer le niveau (User ou System)
if ($UserLevel) {
    $target = "User"
    $targetDesc = "utilisateur courant"
} else {
    $target = "Machine"
    $targetDesc = "système (tous les utilisateurs)"

    # Vérifier les privilèges administrateur
    $isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

    if (-not $isAdmin) {
        Write-Host "❌ Ce script nécessite des privilèges administrateur pour configurer au niveau système." -ForegroundColor $ColorError
        Write-Host ""
        Write-Host "💡 Options:" -ForegroundColor $ColorInfo
        Write-Host "   1. Relancer ce script en tant qu'administrateur" -ForegroundColor $ColorInfo
        Write-Host "   2. Utiliser l'option -UserLevel pour configurer au niveau utilisateur" -ForegroundColor $ColorInfo
        Write-Host ""
        exit 1
    }
}

# Action à effectuer
if ($Disable) {
    $action = "DÉSACTIVATION"
    $value = $null
    $actionDesc = "désactivé"
} else {
    $action = "ACTIVATION"
    $value = "1"
    $actionDesc = "activé"
}

Write-Host "📋 Configuration:" -ForegroundColor $ColorInfo
Write-Host "   Action: $action" -ForegroundColor $ColorInfo
Write-Host "   Niveau: $targetDesc" -ForegroundColor $ColorInfo
Write-Host "   Variable: AUTO_COMMIT" -ForegroundColor $ColorInfo
Write-Host "   Valeur: $(if ($value) { $value } else { '(supprimée)' })" -ForegroundColor $ColorInfo
Write-Host ""

# Confirmation
Write-Host "⚠️  Voulez-vous continuer? (Y/N)" -ForegroundColor $ColorWarning
$response = Read-Host ">"

if ($response -notmatch "^[Yy]$") {
    Write-Host "❌ Opération annulée" -ForegroundColor $ColorWarning
    exit 0
}

Write-Host ""
Write-Host "🔄 Application de la configuration..." -ForegroundColor $ColorInfo

try {
    if ($Disable) {
        # Supprimer la variable
        [Environment]::SetEnvironmentVariable("AUTO_COMMIT", $null, $target)
        Write-Host "✅ AUTO_COMMIT a été $actionDesc pour le niveau: $targetDesc" -ForegroundColor $ColorSuccess
    } else {
        # Définir la variable
        [Environment]::SetEnvironmentVariable("AUTO_COMMIT", $value, $target)
        Write-Host "✅ AUTO_COMMIT a été $actionDesc pour le niveau: $targetDesc" -ForegroundColor $ColorSuccess
    }
} catch {
    Write-Host "❌ Erreur lors de la configuration: $($_.Exception.Message)" -ForegroundColor $ColorError
    exit 1
}

Write-Host ""
Write-Host "============================================================================" -ForegroundColor $ColorInfo
Write-Host "  CONFIGURATION TERMINÉE" -ForegroundColor $ColorInfo
Write-Host "============================================================================" -ForegroundColor $ColorInfo
Write-Host ""

# Afficher l'état actuel
Write-Host "📊 État actuel des variables d'environnement:" -ForegroundColor $ColorInfo
Write-Host ""
Write-Host "AUTO_COMMIT (User):   $(if ([Environment]::GetEnvironmentVariable('AUTO_COMMIT', 'User')) { [Environment]::GetEnvironmentVariable('AUTO_COMMIT', 'User') } else { '(non défini)' })"
Write-Host "AUTO_COMMIT (Machine): $(if ([Environment]::GetEnvironmentVariable('AUTO_COMMIT', 'Machine')) { [Environment]::GetEnvironmentVariable('AUTO_COMMIT', 'Machine') } else { '(non défini)' })"
Write-Host "AUTO_COMMIT (Process): $(if ($env:AUTO_COMMIT) { $env:AUTO_COMMIT } else { '(non défini)' })"
Write-Host ""

# Important: Note sur la propagation
Write-Host "⚠️  IMPORTANT:" -ForegroundColor $ColorWarning
Write-Host "   • Les nouvelles valeurs seront effectives pour les NOUVELLES sessions PowerShell" -ForegroundColor $ColorWarning
Write-Host "   • Cette session PowerShell actuelle n'est PAS mise à jour automatiquement" -ForegroundColor $ColorWarning
Write-Host "   • Pour appliquer immédiatement dans cette session, exécutez:" -ForegroundColor $ColorInfo
Write-Host ""
if ($Disable) {
    Write-Host '     Remove-Item Env:\AUTO_COMMIT' -ForegroundColor $ColorInfo
} else {
    Write-Host '     $env:AUTO_COMMIT = "1"' -ForegroundColor $ColorInfo
}
Write-Host ""

# Information sur les tâches planifiées
Write-Host "💡 Note:" -ForegroundColor $ColorInfo
Write-Host "   • Les tâches planifiées (Task Scheduler) utilisent leurs propres variables d'environnement" -ForegroundColor $ColorInfo
Write-Host "   • Pour mettre à jour les tâches existantes, elles doivent être recréées ou modifiées" -ForegroundColor $ColorInfo
Write-Host "   • Utilisez setup_unified_scheduler.ps1 pour recréer les tâches avec AUTO_COMMIT" -ForegroundColor $ColorInfo
Write-Host ""

Write-Host "============================================================================" -ForegroundColor $ColorInfo
Write-Host ""
