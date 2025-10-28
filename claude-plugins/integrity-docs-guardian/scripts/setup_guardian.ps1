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
# [1/4] CONFIGURATION GIT HOOKS v3.0
# ============================================================================
Write-Host "[1/4] Configuration des Git Hooks v3.0...`n" -ForegroundColor Yellow

# PRE-COMMIT HOOK v3.0
$preCommitContent = @"
#!/bin/sh
# Guardian Pre-Commit Hook v3.0
# Exécute Anima (DocKeeper) v2.0 et Neo (IntegrityWatcher) v2.0
# Mode pre-commit avec working directory scan
# Ne bloque que sur erreurs CRITIQUES, permet warnings

echo ""
echo "🛡️  Guardian v3.0 - Pre-Commit Check"
echo "============================================================"

# Mypy - Vérification type hints (STRICT mode - BLOQUE si erreurs)
echo ""
echo "🔍 [1/3] Mypy (Type Checking - STRICT)..."
python -m mypy src/backend/ > reports/mypy_report.txt 2>&1
MYPY_EXIT=`$?
MYPY_ERRORS=`$(grep "Found .* errors" reports/mypy_report.txt | grep -oE '[0-9]+' | head -1)
if [ -n "`$MYPY_ERRORS" ] && [ "`$MYPY_ERRORS" -gt 0 ]; then
    echo "❌ FAILED: `$MYPY_ERRORS type errors detected"
    echo "   📄 Details: reports/mypy_report.txt"
    echo "   💡 Fix type errors or use --no-verify to bypass"
    echo ""
    echo "❌ Guardian: Commit BLOCKED (mypy errors)"
    echo "============================================================"
    exit 1
else
    echo "✅ PASSED: No type errors"
fi

# Anima (DocKeeper) v2.0 - Vérification documentation
echo ""
echo "📚 [2/3] Anima (DocKeeper) v2.0..."
python claude-plugins/integrity-docs-guardian/scripts/scan_docs.py --mode pre-commit
ANIMA_EXIT=`$?

# Neo (IntegrityWatcher) v2.0 - Vérification intégrité
echo ""
echo "🔍 [3/3] Neo (IntegrityWatcher) v2.0..."
python claude-plugins/integrity-docs-guardian/scripts/check_integrity.py --mode pre-commit
NEO_EXIT=`$?

# Vérifier les exit codes
# Exit 1 = critical (bloque)
# Exit 0 = ok ou warnings (autorise)
CRITICAL=0

if [ `$ANIMA_EXIT -ne 0 ]; then
    CRITICAL=1
fi

if [ `$NEO_EXIT -ne 0 ]; then
    CRITICAL=1
fi

# Résumé final
echo ""
echo "============================================================"
if [ `$CRITICAL -eq 1 ]; then
    echo "❌ Guardian: Commit BLOCKED (critical issues)"
    echo "   Fix critical issues or use --no-verify to bypass"
    echo "============================================================"
    exit 1
else
    echo "✅ Guardian: Pre-commit checks PASSED"
    echo "============================================================"
    exit 0
fi
"@

Set-Content -Path "$hooksDir\pre-commit" -Value $preCommitContent -Encoding UTF8
if ($IsLinux -or $IsMacOS) {
    chmod +x "$hooksDir/pre-commit"
}
Write-Host "   ✅ pre-commit v3.0 configuré (Mypy + Anima v2.0 + Neo v2.0)" -ForegroundColor Green

# POST-COMMIT HOOK v3.0
$postCommitContent = @"
#!/bin/sh
# Guardian Post-Commit Hook v3.0
# Génère le rapport unifié via Nexus + résumé Codex GPT

echo ""
echo "🛡️  Guardian v3.0 - Post-Commit"
echo "============================================================"

# Nexus (Coordinator) - Rapport unifié
echo ""
echo "📊 Nexus (Coordinator) - Generating unified report..."
python claude-plugins/integrity-docs-guardian/scripts/generate_report.py
if [ `$? -eq 0 ]; then
    echo "✅ Unified report generated"
else
    echo "⚠️  Report generation failed (non-blocking)"
fi

# Générer résumé markdown pour Codex GPT
if [ -f "scripts/generate_codex_summary.py" ]; then
    echo ""
    echo "📝 Codex Summary - Generating markdown summary..."
    python scripts/generate_codex_summary.py
    if [ `$? -eq 0 ]; then
        echo "✅ Codex summary generated"
    else
        echo "⚠️  Summary generation failed (non-blocking)"
    fi
fi

# Mise à jour automatique de la documentation si activée
if [ "`$AUTO_UPDATE_DOCS" = "1" ]; then
    echo ""
    echo "📝 Auto-update docs..."
    python claude-plugins/integrity-docs-guardian/scripts/auto_update_docs.py
    if [ `$? -eq 0 ]; then
        echo "✅ Docs updated"
    else
        echo "⚠️  Docs update failed (non-blocking)"
    fi
fi

echo ""
echo "✅ Guardian: Post-commit completed"
echo "============================================================"
exit 0
"@

Set-Content -Path "$hooksDir\post-commit" -Value $postCommitContent -Encoding UTF8
if ($IsLinux -or $IsMacOS) {
    chmod +x "$hooksDir/post-commit"
}
Write-Host "   ✅ post-commit v3.0 configuré (Nexus + Codex Summary)" -ForegroundColor Green

# PRE-PUSH HOOK v3.0
$prePushContent = @"
#!/bin/sh
# Guardian Pre-Push Hook v3.0
# Vérifie l'état de production Cloud Run avant push

echo ""
echo "🛡️  Guardian v3.0 - Pre-Push Check"
echo "============================================================"

# ProdGuardian - Vérification production
echo ""
echo "☁️  ProdGuardian - Checking production health..."
python claude-plugins/integrity-docs-guardian/scripts/check_prod_logs.py
PROD_EXIT=`$?

# Générer résumé markdown pour Codex GPT (avec rapports frais)
if [ -f "scripts/generate_codex_summary.py" ]; then
    echo ""
    echo "📝 Codex Summary - Updating summary..."
    python scripts/generate_codex_summary.py
    if [ `$? -eq 0 ]; then
        echo "✅ Summary updated"
    else
        echo "⚠️  Summary update failed (non-blocking)"
    fi
fi

# Résumé final
echo ""
echo "============================================================"
if [ `$PROD_EXIT -ne 0 ]; then
    echo "❌ Guardian: Push BLOCKED (production critical)"
    echo "   Resolve production issues before pushing"
    echo "   Use --no-verify to bypass (STRONGLY DISCOURAGED)"
    echo "============================================================"
    exit 1
else
    echo "✅ Guardian: Pre-push checks PASSED"
    echo "============================================================"
    exit 0
fi
"@

Set-Content -Path "$hooksDir\pre-push" -Value $prePushContent -Encoding UTF8
if ($IsLinux -or $IsMacOS) {
    chmod +x "$hooksDir/pre-push"
}
Write-Host "   ✅ pre-push v3.0 configuré (ProdGuardian + Codex Summary)`n" -ForegroundColor Green

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
# [3/4] TASK SCHEDULER - Production Monitoring with Notifications
# ============================================================================
Write-Host "[3/4] Configuration Task Scheduler (monitoring prod toutes les ${IntervalHours}h avec notifications)...`n" -ForegroundColor Yellow

$taskName = "EMERGENCE_Guardian_ProdMonitor"
$pwshExe = "C:\Program Files\PowerShell\7\pwsh.exe"

# Fallback sur PowerShell 5 si PowerShell 7 pas trouvé
if (-not (Test-Path $pwshExe)) {
    $pwshExe = "powershell.exe"
}

# Vérifier que le script de monitoring existe
$monitorScript = "$scriptsDir\guardian_monitor_with_notifications.ps1"
if (-not (Test-Path $monitorScript)) {
    Write-Host "   ⚠️  Script de monitoring introuvable - skip Task Scheduler" -ForegroundColor Yellow
    Write-Host ""
} else {
    # Supprimer l'ancienne tâche si existe
    Unregister-ScheduledTask -TaskName $taskName -Confirm:$false -ErrorAction SilentlyContinue

    # Arguments pour le script de monitoring (avec email si fourni)
    $scriptArgs = "-NoProfile -ExecutionPolicy Bypass -File `"$monitorScript`""
    if ($EmailTo) {
        $scriptArgs += " -EmailTo `"$EmailTo`""
    }

    # Créer la tâche
    $action = New-ScheduledTaskAction `
        -Execute $pwshExe `
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
        Write-Host "      Script: guardian_monitor_with_notifications.ps1" -ForegroundColor Gray
        Write-Host "      Intervalle: ${IntervalHours}h" -ForegroundColor Gray
        Write-Host "      Notifications: Toast Windows + Email $(if ($EmailTo) { '✅' } else { '❌' })" -ForegroundColor Gray
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
Write-Host "✅ GUARDIAN v3.0 ACTIVÉ AVEC SUCCÈS" -ForegroundColor Green
Write-Host "================================================================`n" -ForegroundColor Cyan

Write-Host "📋 Configuration active (v3.0):" -ForegroundColor White
Write-Host "   • Pre-commit:  Mypy + Anima v2.0 (docs) + Neo v2.0 (integrity)" -ForegroundColor Gray
Write-Host "      → Mode: Working directory scan (détecte fichiers non commités)" -ForegroundColor DarkGray
Write-Host "   • Post-commit: Nexus (rapport unifié) + Codex Summary + Auto-update docs" -ForegroundColor Gray
Write-Host "   • Pre-push:    ProdGuardian (état production) + Codex Summary" -ForegroundColor Gray
Write-Host "   • Scheduler:   Monitoring prod toutes les ${IntervalHours}h avec notifications Toast Windows" -ForegroundColor Gray
Write-Host ""

Write-Host "🆕 Nouveautés v3.0:" -ForegroundColor White
Write-Host "   ✅ Anima & Neo v2.0 : Détectent les fichiers non commités (working directory)" -ForegroundColor Green
Write-Host "   ✅ Hooks v3.0 : Affichage verbose avec détails complets" -ForegroundColor Green
Write-Host "   ✅ Notifications : Toast Windows natives pour alertes production" -ForegroundColor Green
Write-Host "   ✅ Exit codes : 0=OK/Warning, 1=Critical (bloque uniquement si critique)" -ForegroundColor Green
Write-Host ""

Write-Host "🎯 Commandes utiles:" -ForegroundColor White
Write-Host "   • Audit manuel global:     .\run_audit.ps1" -ForegroundColor Cyan
Write-Host "   • Désactiver Guardian:     .\setup_guardian.ps1 -Disable" -ForegroundColor Cyan
Write-Host "   • Changer intervalle:      .\setup_guardian.ps1 -IntervalHours 2" -ForegroundColor Cyan
Write-Host "   • Avec email:              .\setup_guardian.ps1 -EmailTo 'admin@example.com'" -ForegroundColor Cyan
Write-Host ""

Write-Host "📊 Rapports générés dans:" -ForegroundColor White
Write-Host "   $repoRoot\reports\" -ForegroundColor Gray
Write-Host ""
