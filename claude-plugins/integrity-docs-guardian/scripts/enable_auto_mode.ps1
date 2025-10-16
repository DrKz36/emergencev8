# Script d'activation du mode automatique complet
# Pour ÉMERGENCE - Orchestration automatique des agents

Write-Host "================================================================" -ForegroundColor Cyan
Write-Host "🤖 ACTIVATION DU MODE AUTOMATIQUE COMPLET" -ForegroundColor Cyan
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host ""

# Vérifier si on est dans le bon dossier
$repoRoot = "C:\dev\emergenceV8"
if (-not (Test-Path $repoRoot)) {
    Write-Host "❌ Erreur: Dépôt non trouvé à $repoRoot" -ForegroundColor Red
    exit 1
}

Set-Location $repoRoot

Write-Host "📋 Configuration du mode automatique complet..." -ForegroundColor Yellow
Write-Host ""

# 1. Variables d'environnement pour la session courante
Write-Host "1️⃣ Configuration des variables d'environnement (session courante):" -ForegroundColor Green
$env:AUTO_UPDATE_DOCS = "1"
$env:AUTO_APPLY = "1"
$env:AGENT_CHECK_INTERVAL = "60"
$env:PYTHONIOENCODING = "utf-8"

Write-Host "   ✅ AUTO_UPDATE_DOCS = 1 (hook post-commit activé)" -ForegroundColor White
Write-Host "   ✅ AUTO_APPLY = 1 (mise à jour automatique de la doc)" -ForegroundColor White
Write-Host "   ✅ AGENT_CHECK_INTERVAL = 60 minutes" -ForegroundColor White
Write-Host "   ✅ PYTHONIOENCODING = utf-8" -ForegroundColor White
Write-Host ""

# 2. Ajouter au profil PowerShell pour persistance
Write-Host "2️⃣ Configuration du profil PowerShell (persistance):" -ForegroundColor Green

$profilePath = $PROFILE.CurrentUserAllHosts
if (-not (Test-Path $profilePath)) {
    New-Item -Path $profilePath -ItemType File -Force | Out-Null
    Write-Host "   ✅ Profil PowerShell créé" -ForegroundColor White
}

# Vérifier si les variables sont déjà dans le profil
$profileContent = Get-Content $profilePath -Raw -ErrorAction SilentlyContinue

$varsToAdd = @"

# ÉMERGENCE - Orchestration automatique des agents (ajouté le $(Get-Date -Format 'yyyy-MM-dd HH:mm'))
`$env:AUTO_UPDATE_DOCS = "1"
`$env:AUTO_APPLY = "1"
`$env:AGENT_CHECK_INTERVAL = "60"
`$env:PYTHONIOENCODING = "utf-8"
"@

if ($profileContent -notmatch "AUTO_UPDATE_DOCS") {
    Add-Content -Path $profilePath -Value $varsToAdd
    Write-Host "   ✅ Variables ajoutées au profil PowerShell" -ForegroundColor White
    Write-Host "   📁 Profil: $profilePath" -ForegroundColor Gray
} else {
    Write-Host "   ℹ️  Variables déjà présentes dans le profil" -ForegroundColor Yellow
}
Write-Host ""

# 3. Créer une tâche planifiée pour le scheduler
Write-Host "3️⃣ Configuration de la tâche planifiée Windows:" -ForegroundColor Green

$taskName = "EMERGENCE_AutoOrchestration"
$taskExists = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue

if ($taskExists) {
    Write-Host "   ℹ️  Tâche '$taskName' existe déjà" -ForegroundColor Yellow
    $response = Read-Host "   Voulez-vous la recréer? (O/N)"
    if ($response -eq "O" -or $response -eq "o") {
        Unregister-ScheduledTask -TaskName $taskName -Confirm:$false
        Write-Host "   ✅ Ancienne tâche supprimée" -ForegroundColor White
    } else {
        Write-Host "   ⏭️  Conservation de la tâche existante" -ForegroundColor Yellow
        $taskExists = $null
    }
}

if (-not $taskExists) {
    # Définir l'action
    $pythonExe = (Get-Command python -ErrorAction SilentlyContinue).Source
    if (-not $pythonExe) {
        # Essayer avec le venv
        $pythonExe = "$repoRoot\.venv\Scripts\python.exe"
    }

    $scriptPath = "$repoRoot\claude-plugins\integrity-docs-guardian\scripts\scheduler.py"

    $action = New-ScheduledTaskAction `
        -Execute $pythonExe `
        -Argument "$scriptPath" `
        -WorkingDirectory $repoRoot

    # Définir le déclencheur (au démarrage + toutes les heures)
    $triggerStartup = New-ScheduledTaskTrigger -AtStartup
    $triggerHourly = New-ScheduledTaskTrigger -Once -At (Get-Date) -RepetitionInterval (New-TimeSpan -Hours 1) -RepetitionDuration ([TimeSpan]::MaxValue)

    # Définir les paramètres
    $principal = New-ScheduledTaskPrincipal -UserId "$env:USERDOMAIN\$env:USERNAME" -LogonType Interactive
    $settings = New-ScheduledTaskSettingsSet `
        -AllowStartIfOnBatteries `
        -DontStopIfGoingOnBatteries `
        -StartWhenAvailable `
        -RunOnlyIfNetworkAvailable:$false `
        -DontStopOnIdleEnd

    # Créer la tâche
    try {
        Register-ScheduledTask `
            -TaskName $taskName `
            -Action $action `
            -Trigger $triggerStartup, $triggerHourly `
            -Principal $principal `
            -Settings $settings `
            -Description "ÉMERGENCE - Orchestration automatique des agents de vérification" `
            -ErrorAction Stop | Out-Null

        Write-Host "   ✅ Tâche planifiée '$taskName' créée avec succès" -ForegroundColor White
        Write-Host "   📅 Exécution: Au démarrage + toutes les heures" -ForegroundColor Gray
    } catch {
        Write-Host "   ⚠️  Impossible de créer la tâche planifiée automatiquement" -ForegroundColor Yellow
        Write-Host "   💡 Vous pouvez la créer manuellement via le Planificateur de tâches" -ForegroundColor Yellow
        Write-Host "      Programme: $pythonExe" -ForegroundColor Gray
        Write-Host "      Arguments: $scriptPath" -ForegroundColor Gray
        Write-Host "      Répertoire: $repoRoot" -ForegroundColor Gray
    }
}
Write-Host ""

# 4. Test de l'installation
Write-Host "4️⃣ Test de l'installation:" -ForegroundColor Green
Write-Host "   🔄 Exécution du script de test..." -ForegroundColor White

$testScript = "$repoRoot\claude-plugins\integrity-docs-guardian\scripts\test_installation.py"
if (Test-Path $testScript) {
    & python $testScript
} else {
    Write-Host "   ⚠️  Script de test non trouvé" -ForegroundColor Yellow
}
Write-Host ""

# 5. Résumé final
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host "✅ MODE AUTOMATIQUE COMPLET ACTIVÉ" -ForegroundColor Green
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "📋 Configuration appliquée:" -ForegroundColor Yellow
Write-Host "   ✅ Hook Git post-commit: ACTIVÉ" -ForegroundColor White
Write-Host "      → Les agents s'exécutent automatiquement après chaque commit" -ForegroundColor Gray
Write-Host ""
Write-Host "   ✅ Mise à jour automatique de la doc: ACTIVÉE" -ForegroundColor White
Write-Host "      → Les mises à jour sont appliquées et commitées automatiquement" -ForegroundColor Gray
Write-Host ""
Write-Host "   ✅ Planificateur périodique: ACTIVÉ (toutes les heures)" -ForegroundColor White
Write-Host "      → Surveillance continue même sans commit" -ForegroundColor Gray
Write-Host ""

Write-Host "💡 Prochaines étapes:" -ForegroundColor Yellow
Write-Host "   1. Redémarrer PowerShell pour charger les variables du profil" -ForegroundColor White
Write-Host "   2. Faire un commit pour tester le hook automatique" -ForegroundColor White
Write-Host "   3. Vérifier les logs: claude-plugins\integrity-docs-guardian\logs\" -ForegroundColor White
Write-Host ""

Write-Host "🛠️  Commandes utiles:" -ForegroundColor Yellow
Write-Host "   # Désactiver le mode automatique" -ForegroundColor Gray
Write-Host "   .\claude-plugins\integrity-docs-guardian\scripts\disable_auto_mode.ps1" -ForegroundColor Cyan
Write-Host ""
Write-Host "   # Voir l'état de la tâche planifiée" -ForegroundColor Gray
Write-Host "   Get-ScheduledTask -TaskName 'EMERGENCE_AutoOrchestration'" -ForegroundColor Cyan
Write-Host ""
Write-Host "   # Test manuel" -ForegroundColor Gray
Write-Host "   python claude-plugins\integrity-docs-guardian\scripts\auto_orchestrator.py" -ForegroundColor Cyan
Write-Host ""

Write-Host "================================================================" -ForegroundColor Cyan
Write-Host ""
