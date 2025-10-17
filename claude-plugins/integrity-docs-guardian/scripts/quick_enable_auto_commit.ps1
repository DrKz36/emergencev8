# ============================================================================
# QUICK ENABLE AUTO_COMMIT - Activation Rapide en Un Clic
# ============================================================================
# Ce script active rapidement AUTO_COMMIT pour les agents Guardian
# en reconfigurant la tâche planifiée Windows
# ============================================================================

$ColorSuccess = "Green"
$ColorWarning = "Yellow"
$ColorError = "Red"
$ColorInfo = "Cyan"

Write-Host ""
Write-Host "╔══════════════════════════════════════════════════════════════╗" -ForegroundColor $ColorInfo
Write-Host "║                                                              ║" -ForegroundColor $ColorInfo
Write-Host "║    🚀 ACTIVATION RAPIDE DU COMMIT AUTOMATIQUE                ║" -ForegroundColor $ColorInfo
Write-Host "║       Agents Guardian ÉMERGENCE                              ║" -ForegroundColor $ColorInfo
Write-Host "║                                                              ║" -ForegroundColor $ColorInfo
Write-Host "╚══════════════════════════════════════════════════════════════╝" -ForegroundColor $ColorInfo
Write-Host ""

# Vérifier les privilèges administrateur
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not $isAdmin) {
    Write-Host "⚠️  Ce script nécessite des privilèges administrateur" -ForegroundColor $ColorWarning
    Write-Host ""
    Write-Host "💡 Veuillez relancer PowerShell en tant qu'administrateur" -ForegroundColor $ColorInfo
    Write-Host ""
    Write-Host "Comment faire :" -ForegroundColor $ColorInfo
    Write-Host "  1. Fermer cette fenêtre" -ForegroundColor Gray
    Write-Host "  2. Clic droit sur PowerShell" -ForegroundColor Gray
    Write-Host "  3. Sélectionner 'Exécuter en tant qu'administrateur'" -ForegroundColor Gray
    Write-Host "  4. Relancer ce script" -ForegroundColor Gray
    Write-Host ""

    Read-Host "Appuyez sur Entrée pour quitter"
    exit 1
}

Write-Host "✅ Privilèges administrateur confirmés" -ForegroundColor $ColorSuccess
Write-Host ""

# Configuration
$repoRoot = "C:\dev\emergenceV8"
$scriptsDir = Join-Path $repoRoot "claude-plugins\integrity-docs-guardian\scripts"
$setupScript = Join-Path $scriptsDir "setup_unified_scheduler.ps1"

# Vérifier l'existence du script
if (-not (Test-Path $setupScript)) {
    Write-Host "❌ Erreur: Script de configuration introuvable" -ForegroundColor $ColorError
    Write-Host "   Chemin recherché: $setupScript" -ForegroundColor $ColorError
    Write-Host ""
    Read-Host "Appuyez sur Entrée pour quitter"
    exit 1
}

# Afficher l'information
Write-Host "📋 Configuration à appliquer:" -ForegroundColor $ColorInfo
Write-Host "   • AUTO_COMMIT: ACTIVÉ" -ForegroundColor $ColorSuccess
Write-Host "   • Tâche planifiée: Sera reconfigurée" -ForegroundColor $ColorInfo
Write-Host "   • Intervalle: 60 minutes (par défaut)" -ForegroundColor $ColorInfo
Write-Host ""

Write-Host "⚠️  AVERTISSEMENT:" -ForegroundColor $ColorWarning
Write-Host "   Avec AUTO_COMMIT activé, les agents Guardian committent" -ForegroundColor $ColorWarning
Write-Host "   automatiquement les changements détectés SANS CONFIRMATION." -ForegroundColor $ColorWarning
Write-Host ""
Write-Host "   Assurez-vous d'avoir une sauvegarde de votre code avant de continuer." -ForegroundColor $ColorWarning
Write-Host ""

# Demander confirmation
Write-Host "Voulez-vous continuer? (O/N)" -ForegroundColor $ColorInfo
$response = Read-Host ">"

if ($response -notmatch "^[OoYy]$") {
    Write-Host ""
    Write-Host "❌ Opération annulée" -ForegroundColor $ColorWarning
    Write-Host ""
    Read-Host "Appuyez sur Entrée pour quitter"
    exit 0
}

Write-Host ""
Write-Host "════════════════════════════════════════════════════════════════" -ForegroundColor $ColorInfo
Write-Host ""
Write-Host "🔄 Reconfiguration de la tâche planifiée..." -ForegroundColor $ColorInfo
Write-Host ""

# Se placer dans le répertoire des scripts
Set-Location $scriptsDir

# Exécuter le script de configuration avec AUTO_COMMIT activé
try {
    & $setupScript -Force -EnableAutoCommit

    if ($LASTEXITCODE -eq 0 -or $null -eq $LASTEXITCODE) {
        Write-Host ""
        Write-Host "════════════════════════════════════════════════════════════════" -ForegroundColor $ColorSuccess
        Write-Host ""
        Write-Host "✅ AUTO_COMMIT ACTIVÉ AVEC SUCCÈS!" -ForegroundColor $ColorSuccess
        Write-Host ""
        Write-Host "La tâche planifiée 'EmergenceUnifiedGuardian' a été configurée" -ForegroundColor $ColorSuccess
        Write-Host "avec le commit automatique activé." -ForegroundColor $ColorSuccess
        Write-Host ""
        Write-Host "════════════════════════════════════════════════════════════════" -ForegroundColor $ColorSuccess
        Write-Host ""

        # Afficher les prochaines étapes
        Write-Host "📊 Prochaines étapes:" -ForegroundColor $ColorInfo
        Write-Host ""
        Write-Host "1. Vérifier la tâche:" -ForegroundColor Gray
        Write-Host "   Get-ScheduledTask -TaskName 'EmergenceUnifiedGuardian'" -ForegroundColor $ColorInfo
        Write-Host ""
        Write-Host "2. Tester immédiatement:" -ForegroundColor Gray
        Write-Host "   Start-ScheduledTask -TaskName 'EmergenceUnifiedGuardian'" -ForegroundColor $ColorInfo
        Write-Host ""
        Write-Host "3. Voir les logs:" -ForegroundColor Gray
        Write-Host "   Get-Content ..\logs\unified_scheduler_*.log -Tail 50" -ForegroundColor $ColorInfo
        Write-Host ""
        Write-Host "4. Vérifier l'historique Git:" -ForegroundColor Gray
        Write-Host "   git log --all --oneline --grep='chore(sync)' -n 10" -ForegroundColor $ColorInfo
        Write-Host ""

        # Proposer un test
        Write-Host "═══════════════════════════════════════════════════════════════" -ForegroundColor $ColorInfo
        Write-Host ""
        Write-Host "🧪 Voulez-vous tester la tâche maintenant? (O/N)" -ForegroundColor $ColorInfo
        $testResponse = Read-Host ">"

        if ($testResponse -match "^[OoYy]$") {
            Write-Host ""
            Write-Host "🚀 Lancement du test..." -ForegroundColor $ColorInfo
            Write-Host ""

            Start-ScheduledTask -TaskName "EmergenceUnifiedGuardian"

            Write-Host "⏳ Attente de 10 secondes..." -ForegroundColor $ColorInfo
            Start-Sleep -Seconds 10

            Write-Host ""
            Write-Host "📊 Résultat du test:" -ForegroundColor $ColorInfo
            $taskInfo = Get-ScheduledTaskInfo -TaskName "EmergenceUnifiedGuardian"
            Write-Host "   Dernière exécution: $($taskInfo.LastRunTime)" -ForegroundColor Gray
            Write-Host "   Résultat: $($taskInfo.LastTaskResult)" -ForegroundColor $(if ($taskInfo.LastTaskResult -eq 0) { $ColorSuccess } else { $ColorWarning })
            Write-Host ""

            if ($taskInfo.LastTaskResult -eq 0) {
                Write-Host "✅ Test réussi!" -ForegroundColor $ColorSuccess
            } else {
                Write-Host "⚠️  Vérifiez les logs pour plus de détails" -ForegroundColor $ColorWarning
            }
            Write-Host ""
        }

    } else {
        Write-Host ""
        Write-Host "❌ Erreur lors de la configuration" -ForegroundColor $ColorError
        Write-Host "   Code de sortie: $LASTEXITCODE" -ForegroundColor $ColorError
        Write-Host ""
    }

} catch {
    Write-Host ""
    Write-Host "❌ Erreur lors de l'exécution:" -ForegroundColor $ColorError
    Write-Host "   $($_.Exception.Message)" -ForegroundColor $ColorError
    Write-Host ""
}

Write-Host "════════════════════════════════════════════════════════════════" -ForegroundColor $ColorInfo
Write-Host ""
Write-Host "📖 Pour plus d'informations:" -ForegroundColor $ColorInfo
Write-Host "   ..\AUTO_COMMIT_GUIDE.md        - Guide complet" -ForegroundColor Gray
Write-Host "   ..\AUTO_COMMIT_ACTIVATION.md   - Guide rapide" -ForegroundColor Gray
Write-Host ""

Read-Host "Appuyez sur Entrée pour quitter"
