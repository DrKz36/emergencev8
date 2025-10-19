# ============================================================================
# GUARDIAN SETUP - Configuration automatique complète
# ============================================================================
# Configure les Git Hooks et Task Scheduler pour monitoring automatique
# Usage: .\setup_guardian.ps1 [-Disable] [-IntervalHours 2]
# ============================================================================

param(
    [switch]$Disable,
    [int]$IntervalHours = 6,
    [string]$EmailTo = ""
)

Write-Host "`n================================================================" -ForegroundColor Cyan
Write-Host "🛡️  GUARDIAN SETUP - ÉMERGENCE V8" -ForegroundColor Cyan
Write-Host "================================================================`n" -ForegroundColor Cyan

$repoRoot = "C:\dev\emergenceV8"
$guardianDir = "$repoRoot\claude-plugins\integrity-docs-guardian"
$scriptsDir = "$guardianDir\scripts"
$hooksDir = "$repoRoot\.git\hooks"

# ============================================================================
# DÉSACTIVATION
# ============================================================================
if ($Disable) {
    Write-Host "🔴 DÉSACTIVATION DU GUARDIAN`n" -ForegroundColor Yellow

    # Supprimer les hooks Git
    Write-Host "[1/2] Suppression des hooks Git..." -ForegroundColor White
    Remove-Item "$hooksDir\pre-commit" -ErrorAction SilentlyContinue
    Remove-Item "$hooksDir\post-commit" -ErrorAction SilentlyContinue
    Remove-Item "$hooksDir\pre-push" -ErrorAction SilentlyContinue
    Write-Host "   ✅ Hooks supprimés`n" -ForegroundColor Green

    # Supprimer la tâche planifiée
    Write-Host "[2/2] Suppression de la tâche planifiée..." -ForegroundColor White
    Unregister-ScheduledTask -TaskName "EMERGENCE_Guardian_ProdMonitor" -Confirm:$false -ErrorAction SilentlyContinue
    Write-Host "   ✅ Tâche supprimée`n" -ForegroundColor Green

    Write-Host "✅ Guardian désactivé avec succès`n" -ForegroundColor Green
    exit 0
}

# ============================================================================
# ACTIVATION
# ============================================================================
Write-Host "🟢 ACTIVATION DU GUARDIAN`n" -ForegroundColor Green

# Vérifier que les scripts existent
$requiredScripts = @(
    "$scriptsDir\master_orchestrator.py",
    "$scriptsDir\scan_docs.py",
    "$scriptsDir\check_integrity.py",
    "$scriptsDir\check_prod_logs.py",
    "$scriptsDir\generate_report.py"
)

foreach ($script in $requiredScripts) {
    if (-not (Test-Path $script)) {
        Write-Host "❌ Script manquant: $script" -ForegroundColor Red
        exit 1
    }
}

# ============================================================================
# [1/4] CONFIGURATION GIT HOOKS
# ============================================================================
Write-Host "[1/4] Configuration des Git Hooks...`n" -ForegroundColor Yellow

# PRE-COMMIT HOOK
$preCommitContent = @"
#!/bin/sh
# Guardian Pre-Commit Hook
# Exécute Anima (DocKeeper) et Neo (IntegrityWatcher)

echo "🛡️  Guardian Pre-Commit Check..."

# Anima (DocKeeper) - Vérification documentation
echo "📚 Anima (DocKeeper)..."
python claude-plugins/integrity-docs-guardian/scripts/scan_docs.py
ANIMA_EXIT=`$?

# Neo (IntegrityWatcher) - Vérification intégrité
echo "🔍 Neo (IntegrityWatcher)..."
python claude-plugins/integrity-docs-guardian/scripts/check_integrity.py
NEO_EXIT=`$?

# Bloquer le commit si erreur critique
if [ `$ANIMA_EXIT -ne 0 ] || [ `$NEO_EXIT -ne 0 ]; then
    echo "❌ Guardian: Erreurs critiques détectées - commit bloqué"
    echo "   Utilisez --no-verify pour bypasser (déconseillé)"
    exit 1
fi

echo "✅ Guardian: Pre-commit OK"
exit 0
"@

Set-Content -Path "$hooksDir\pre-commit" -Value $preCommitContent -Encoding UTF8
if ($IsLinux -or $IsMacOS) {
    chmod +x "$hooksDir/pre-commit"
}
Write-Host "   ✅ pre-commit configuré (Anima + Neo)" -ForegroundColor Green

# POST-COMMIT HOOK
$postCommitContent = @"
#!/bin/sh
# Guardian Post-Commit Hook
# Génère le rapport unifié via Nexus

echo "🛡️  Guardian Post-Commit..."

# Nexus (Coordinator) - Rapport unifié
echo "📊 Nexus (Coordinator)..."
python claude-plugins/integrity-docs-guardian/scripts/generate_report.py

# Mise à jour automatique de la documentation si activée
if [ "`$AUTO_UPDATE_DOCS" = "1" ]; then
    echo "📝 Auto-update docs..."
    python claude-plugins/integrity-docs-guardian/scripts/auto_update_docs.py
fi

echo "✅ Guardian: Post-commit OK"
exit 0
"@

Set-Content -Path "$hooksDir\post-commit" -Value $postCommitContent -Encoding UTF8
if ($IsLinux -or $IsMacOS) {
    chmod +x "$hooksDir/post-commit"
}
Write-Host "   ✅ post-commit configuré (Nexus)" -ForegroundColor Green

# PRE-PUSH HOOK
$prePushContent = @"
#!/bin/sh
# Guardian Pre-Push Hook
# Vérifie l'état de production Cloud Run avant push

echo "🛡️  Guardian Pre-Push Check..."

# ProdGuardian - Vérification production
echo "☁️  ProdGuardian..."
python claude-plugins/integrity-docs-guardian/scripts/check_prod_logs.py
PROD_EXIT=`$?

# Bloquer le push si production en état CRITICAL
if [ `$PROD_EXIT -ne 0 ]; then
    echo "❌ Guardian: Production en état CRITICAL - push bloqué"
    echo "   Résolvez les erreurs prod avant de pusher"
    echo "   Utilisez --no-verify pour bypasser (TRÈS déconseillé)"
    exit 1
fi

echo "✅ Guardian: Pre-push OK"
exit 0
"@

Set-Content -Path "$hooksDir\pre-push" -Value $prePushContent -Encoding UTF8
if ($IsLinux -or $IsMacOS) {
    chmod +x "$hooksDir/pre-push"
}
Write-Host "   ✅ pre-push configuré (ProdGuardian)`n" -ForegroundColor Green

# ============================================================================
# [2/4] VARIABLES D'ENVIRONNEMENT
# ============================================================================
Write-Host "[2/4] Configuration des variables d'environnement...`n" -ForegroundColor Yellow

$env:AUTO_UPDATE_DOCS = "1"
$env:PYTHONIOENCODING = "utf-8"

# Ajouter au profil PowerShell pour persistance
$profilePath = $PROFILE.CurrentUserAllHosts
if (-not (Test-Path $profilePath)) {
    New-Item -Path $profilePath -ItemType File -Force | Out-Null
}

$profileContent = Get-Content $profilePath -Raw -ErrorAction SilentlyContinue

if ($profileContent -notmatch "AUTO_UPDATE_DOCS") {
    $varsToAdd = @"

# EMERGENCE Guardian - Auto-update (ajouté le $(Get-Date -Format 'yyyy-MM-dd HH:mm'))
`$env:AUTO_UPDATE_DOCS = "1"
`$env:PYTHONIOENCODING = "utf-8"
"@
    Add-Content -Path $profilePath -Value $varsToAdd
    Write-Host "   ✅ Variables ajoutées au profil PowerShell" -ForegroundColor Green
} else {
    Write-Host "   ℹ️  Variables déjà présentes dans le profil" -ForegroundColor Gray
}
Write-Host ""

# ============================================================================
# [3/4] TASK SCHEDULER - Production Monitoring
# ============================================================================
Write-Host "[3/4] Configuration Task Scheduler (monitoring prod toutes les ${IntervalHours}h)...`n" -ForegroundColor Yellow

$taskName = "EMERGENCE_Guardian_ProdMonitor"
$pythonExe = "$repoRoot\.venv\Scripts\python.exe"

# Fallback sur Python global si venv pas trouvé
if (-not (Test-Path $pythonExe)) {
    $pythonExe = (Get-Command python -ErrorAction SilentlyContinue).Source
    if (-not $pythonExe) {
        Write-Host "   ⚠️  Python introuvable - skip Task Scheduler" -ForegroundColor Yellow
        Write-Host ""
    }
}

if ($pythonExe) {
    # Supprimer l'ancienne tâche si existe
    Unregister-ScheduledTask -TaskName $taskName -Confirm:$false -ErrorAction SilentlyContinue

    # Arguments pour ProdGuardian (avec email si fourni)
    $scriptArgs = "$scriptsDir\check_prod_logs.py"
    if ($EmailTo) {
        $scriptArgs += " --email $EmailTo"
    }

    # Créer la tâche
    $action = New-ScheduledTaskAction `
        -Execute $pythonExe `
        -Argument $scriptArgs `
        -WorkingDirectory $repoRoot

    $trigger = New-ScheduledTaskTrigger `
        -Once `
        -At (Get-Date).AddMinutes(5) `
        -RepetitionInterval (New-TimeSpan -Hours $IntervalHours)

    $settings = New-ScheduledTaskSettingsSet `
        -AllowStartIfOnBatteries `
        -DontStopIfGoingOnBatteries `
        -StartWhenAvailable

    Register-ScheduledTask `
        -TaskName $taskName `
        -Action $action `
        -Trigger $trigger `
        -Settings $settings `
        -Description "EMERGENCE - Production monitoring (toutes les ${IntervalHours}h)" `
        -ErrorAction SilentlyContinue | Out-Null

    if (Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue) {
        Write-Host "   ✅ Tâche planifiée créée: $taskName" -ForegroundColor Green
        Write-Host "      Intervalle: ${IntervalHours}h" -ForegroundColor Gray
        if ($EmailTo) {
            Write-Host "      Email: $EmailTo" -ForegroundColor Gray
        }
    } else {
        Write-Host "   ⚠️  Impossible de créer la tâche (droits admin requis?)" -ForegroundColor Yellow
    }
    Write-Host ""
}

# ============================================================================
# [4/4] TEST DE VALIDATION
# ============================================================================
Write-Host "[4/4] Test de validation...`n" -ForegroundColor Yellow

Write-Host "   🧪 Test Anima..." -ForegroundColor Gray
$animaResult = & python "$scriptsDir\scan_docs.py" 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Host "      ✅ Anima OK" -ForegroundColor Green
} else {
    Write-Host "      ⚠️  Anima a détecté des problèmes (normal si première config)" -ForegroundColor Yellow
}

Write-Host "   🧪 Test Neo..." -ForegroundColor Gray
$neoResult = & python "$scriptsDir\check_integrity.py" 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Host "      ✅ Neo OK" -ForegroundColor Green
} else {
    Write-Host "      ⚠️  Neo a détecté des problèmes (normal si première config)" -ForegroundColor Yellow
}

Write-Host ""

# ============================================================================
# RÉSUMÉ FINAL
# ============================================================================
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host "✅ GUARDIAN ACTIVÉ AVEC SUCCÈS" -ForegroundColor Green
Write-Host "================================================================`n" -ForegroundColor Cyan

Write-Host "📋 Configuration active:" -ForegroundColor White
Write-Host "   • Pre-commit:  Anima (docs) + Neo (integrity)" -ForegroundColor Gray
Write-Host "   • Post-commit: Nexus (rapport unifié) + Auto-update docs" -ForegroundColor Gray
Write-Host "   • Pre-push:    ProdGuardian (état production)" -ForegroundColor Gray
Write-Host "   • Scheduler:   ProdGuardian toutes les ${IntervalHours}h" -ForegroundColor Gray
Write-Host ""

Write-Host "🎯 Commandes utiles:" -ForegroundColor White
Write-Host "   • Audit manuel global:     .\run_audit.ps1" -ForegroundColor Cyan
Write-Host "   • Désactiver Guardian:     .\setup_guardian.ps1 -Disable" -ForegroundColor Cyan
Write-Host "   • Changer intervalle:      .\setup_guardian.ps1 -IntervalHours 2" -ForegroundColor Cyan
Write-Host "   • Avec email:              .\setup_guardian.ps1 -EmailTo 'admin@example.com'" -ForegroundColor Cyan
Write-Host ""

Write-Host "📊 Rapports générés dans:" -ForegroundColor White
Write-Host "   $guardianDir\reports\" -ForegroundColor Gray
Write-Host ""
