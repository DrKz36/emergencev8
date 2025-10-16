# Script de désactivation du mode automatique
# Pour ÉMERGENCE - Orchestration automatique des agents

Write-Host "================================================================" -ForegroundColor Cyan
Write-Host "⏹️  DÉSACTIVATION DU MODE AUTOMATIQUE" -ForegroundColor Cyan
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host ""

# Vérifier si on est dans le bon dossier
$repoRoot = "C:\dev\emergenceV8"
if (-not (Test-Path $repoRoot)) {
    Write-Host "❌ Erreur: Dépôt non trouvé à $repoRoot" -ForegroundColor Red
    exit 1
}

Set-Location $repoRoot

Write-Host "📋 Désactivation du mode automatique..." -ForegroundColor Yellow
Write-Host ""

# 1. Variables d'environnement pour la session courante
Write-Host "1️⃣ Désactivation des variables d'environnement (session courante):" -ForegroundColor Green
$env:AUTO_UPDATE_DOCS = "0"
$env:AUTO_APPLY = "0"

Write-Host "   ✅ AUTO_UPDATE_DOCS = 0 (hook post-commit désactivé)" -ForegroundColor White
Write-Host "   ✅ AUTO_APPLY = 0 (mise à jour manuelle uniquement)" -ForegroundColor White
Write-Host ""

# 2. Retirer du profil PowerShell
Write-Host "2️⃣ Nettoyage du profil PowerShell:" -ForegroundColor Green

$profilePath = $PROFILE.CurrentUserAllHosts
if (Test-Path $profilePath) {
    $profileContent = Get-Content $profilePath -Raw

    if ($profileContent -match "AUTO_UPDATE_DOCS") {
        # Supprimer les lignes relatives à l'orchestration automatique
        $newContent = $profileContent -replace '(?ms)# ÉMERGENCE - Orchestration automatique.*?(?=\r?\n\r?\n|\Z)', ''
        $newContent = $newContent.Trim()

        Set-Content -Path $profilePath -Value $newContent
        Write-Host "   ✅ Variables retirées du profil PowerShell" -ForegroundColor White
    } else {
        Write-Host "   ℹ️  Aucune variable trouvée dans le profil" -ForegroundColor Yellow
    }
} else {
    Write-Host "   ℹ️  Profil PowerShell non trouvé" -ForegroundColor Yellow
}
Write-Host ""

# 3. Supprimer/désactiver la tâche planifiée
Write-Host "3️⃣ Gestion de la tâche planifiée Windows:" -ForegroundColor Green

$taskName = "EMERGENCE_AutoOrchestration"
$task = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue

if ($task) {
    $response = Read-Host "   Voulez-vous SUPPRIMER la tâche planifiée? (O=Supprimer, D=Désactiver, N=Garder) [O/D/N]"

    switch ($response.ToUpper()) {
        "O" {
            Unregister-ScheduledTask -TaskName $taskName -Confirm:$false
            Write-Host "   ✅ Tâche planifiée '$taskName' supprimée" -ForegroundColor White
        }
        "D" {
            Disable-ScheduledTask -TaskName $taskName | Out-Null
            Write-Host "   ✅ Tâche planifiée '$taskName' désactivée" -ForegroundColor White
        }
        default {
            Write-Host "   ℹ️  Tâche planifiée conservée (inchangée)" -ForegroundColor Yellow
        }
    }
} else {
    Write-Host "   ℹ️  Aucune tâche planifiée trouvée" -ForegroundColor Yellow
}
Write-Host ""

# 4. Arrêter le scheduler s'il tourne
Write-Host "4️⃣ Vérification du scheduler:" -ForegroundColor Green

$schedulerProcess = Get-Process -Name python -ErrorAction SilentlyContinue | Where-Object {
    $_.CommandLine -like "*scheduler.py*"
}

if ($schedulerProcess) {
    Write-Host "   ⚠️  Processus scheduler détecté (PID: $($schedulerProcess.Id))" -ForegroundColor Yellow
    $response = Read-Host "   Voulez-vous l'arrêter? (O/N)"

    if ($response -eq "O" -or $response -eq "o") {
        Stop-Process -Id $schedulerProcess.Id -Force
        Write-Host "   ✅ Processus scheduler arrêté" -ForegroundColor White
    } else {
        Write-Host "   ℹ️  Processus scheduler conservé" -ForegroundColor Yellow
    }
} else {
    Write-Host "   ℹ️  Aucun processus scheduler actif" -ForegroundColor Yellow
}
Write-Host ""

# 5. Résumé final
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host "✅ MODE AUTOMATIQUE DÉSACTIVÉ" -ForegroundColor Green
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "📋 État actuel:" -ForegroundColor Yellow
Write-Host "   ❌ Hook Git post-commit: DÉSACTIVÉ" -ForegroundColor White
Write-Host "      → Les agents ne s'exécutent plus automatiquement après commit" -ForegroundColor Gray
Write-Host ""
Write-Host "   ❌ Mise à jour automatique de la doc: DÉSACTIVÉE" -ForegroundColor White
Write-Host "      → Mode manuel uniquement" -ForegroundColor Gray
Write-Host ""
Write-Host "   ❌ Planificateur périodique: ARRÊTÉ" -ForegroundColor White
Write-Host "      → Pas de surveillance continue" -ForegroundColor Gray
Write-Host ""

Write-Host "💡 Vous pouvez toujours exécuter manuellement:" -ForegroundColor Yellow
Write-Host "   # Orchestration manuelle" -ForegroundColor Gray
Write-Host "   python claude-plugins\integrity-docs-guardian\scripts\auto_orchestrator.py" -ForegroundColor Cyan
Write-Host ""
Write-Host "   # Avec slash command Claude" -ForegroundColor Gray
Write-Host "   /auto_sync" -ForegroundColor Cyan
Write-Host ""
Write-Host "   # Réactiver le mode automatique" -ForegroundColor Gray
Write-Host "   .\claude-plugins\integrity-docs-guardian\scripts\enable_auto_mode.ps1" -ForegroundColor Cyan
Write-Host ""

Write-Host "================================================================" -ForegroundColor Cyan
Write-Host ""
