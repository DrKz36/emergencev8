# Script pour créer des tâches planifiées Windows (3x/jour)
# ÉMERGENCE V8 - Audit automatisé local
# ⚠️ IMPORTANT: Ton PC doit rester allumé pour que ça fonctionne

param(
    [string]$PythonPath = "python",
    [string]$ScriptPath = "$PSScriptRoot\run_audit.py"
)

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  CONFIGURATION TASK SCHEDULER WINDOWS" -ForegroundColor Cyan
Write-Host "  ⚠️  TON PC DOIT RESTER ALLUMÉ" -ForegroundColor Yellow
Write-Host "============================================================`n" -ForegroundColor Cyan

# Vérifier si on est admin
$IsAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not $IsAdmin) {
    Write-Host "❌ Ce script nécessite les droits administrateur" -ForegroundColor Red
    Write-Host "   Relance PowerShell en tant qu'administrateur`n" -ForegroundColor Yellow
    exit 1
}

# Vérifier que Python est disponible
$PythonVersion = & $PythonPath --version 2>&1

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Python non trouvé à: $PythonPath" -ForegroundColor Red
    Write-Host "   Spécifie le chemin complet avec -PythonPath`n" -ForegroundColor Yellow
    exit 1
}

Write-Host "✅ Python trouvé: $PythonVersion`n" -ForegroundColor Green

# Vérifier que le script existe
if (-not (Test-Path $ScriptPath)) {
    Write-Host "❌ Script non trouvé: $ScriptPath" -ForegroundColor Red
    exit 1
}

Write-Host "✅ Script trouvé: $ScriptPath`n" -ForegroundColor Green

# Définir les tâches (3x/jour)
$Tasks = @(
    @{
        Name = "Emergence-Audit-Morning"
        Time = "08:00"
        Description = "Audit ÉMERGENCE matinal (08:00)"
    },
    @{
        Name = "Emergence-Audit-Afternoon"
        Time = "14:00"
        Description = "Audit ÉMERGENCE après-midi (14:00)"
    },
    @{
        Name = "Emergence-Audit-Evening"
        Time = "20:00"
        Description = "Audit ÉMERGENCE soirée (20:00)"
    }
)

Write-Host "[1/3] Création des tâches planifiées...`n" -ForegroundColor Yellow

foreach ($Task in $Tasks) {
    Write-Host "  Création: $($Task.Description)..." -ForegroundColor Cyan

    # Supprimer la tâche existante si présente
    Unregister-ScheduledTask -TaskName $Task.Name -Confirm:$false -ErrorAction SilentlyContinue

    # Action: exécuter le script Python
    $Action = New-ScheduledTaskAction `
        -Execute $PythonPath `
        -Argument "`"$ScriptPath`" --target emergence-app-00501-zon --mode full" `
        -WorkingDirectory (Split-Path $ScriptPath)

    # Trigger: tous les jours à l'heure spécifiée
    $Trigger = New-ScheduledTaskTrigger `
        -Daily `
        -At $Task.Time

    # Settings
    $Settings = New-ScheduledTaskSettingsSet `
        -AllowStartIfOnBatteries `
        -DontStopIfGoingOnBatteries `
        -StartWhenAvailable `
        -RunOnlyIfNetworkAvailable `
        -ExecutionTimeLimit (New-TimeSpan -Minutes 15)

    # Principal: exécuter avec l'utilisateur courant
    $Principal = New-ScheduledTaskPrincipal `
        -UserId "$env:USERDOMAIN\$env:USERNAME" `
        -LogonType Interactive `
        -RunLevel Highest

    # Créer la tâche
    Register-ScheduledTask `
        -TaskName $Task.Name `
        -Description $Task.Description `
        -Action $Action `
        -Trigger $Trigger `
        -Settings $Settings `
        -Principal $Principal `
        -Force | Out-Null

    if ($?) {
        Write-Host "  ✅ $($Task.Name) créée" -ForegroundColor Green
    } else {
        Write-Host "  ❌ Erreur création $($Task.Name)" -ForegroundColor Red
    }
}

Write-Host "`n✅ Tâches planifiées créées`n" -ForegroundColor Green

# Afficher les tâches créées
Write-Host "[2/3] Vérification des tâches..." -ForegroundColor Yellow

foreach ($Task in $Tasks) {
    $ScheduledTask = Get-ScheduledTask -TaskName $Task.Name -ErrorAction SilentlyContinue

    if ($ScheduledTask) {
        $NextRun = (Get-ScheduledTaskInfo -TaskName $Task.Name).NextRunTime
        Write-Host "  ✅ $($Task.Name)" -ForegroundColor Green
        Write-Host "     Prochaine exécution: $NextRun" -ForegroundColor Cyan
    } else {
        Write-Host "  ❌ $($Task.Name) non trouvée" -ForegroundColor Red
    }
}

# Test optionnel
Write-Host "`n[3/3] Test des tâches..." -ForegroundColor Yellow
$RunTest = Read-Host "Lancer un test maintenant? (o/n)"

if ($RunTest -eq "o") {
    Write-Host "`n  Lancement du test..." -ForegroundColor Cyan
    Write-Host "  (Cela peut prendre quelques minutes)"`n -ForegroundColor Yellow

    Start-ScheduledTask -TaskName $Tasks[0].Name

    # Attendre quelques secondes
    Start-Sleep -Seconds 5

    # Vérifier le statut
    $TaskInfo = Get-ScheduledTaskInfo -TaskName $Tasks[0].Name

    Write-Host "  Dernière exécution: $($TaskInfo.LastRunTime)" -ForegroundColor Cyan
    Write-Host "  Résultat: $($TaskInfo.LastTaskResult)" -ForegroundColor Cyan

    if ($TaskInfo.LastTaskResult -eq 0) {
        Write-Host "`n  ✅ Test réussi - vérifiez votre email!" -ForegroundColor Green
    } else {
        Write-Host "`n  ⚠️  Code de sortie: $($TaskInfo.LastTaskResult)" -ForegroundColor Yellow
        Write-Host "  Consultez les logs Task Scheduler pour plus de détails" -ForegroundColor Yellow
    }
} else {
    Write-Host "  Test ignoré" -ForegroundColor Yellow
}

Write-Host "`n============================================================" -ForegroundColor Cyan
Write-Host "  ✅ CONFIGURATION TERMINÉE" -ForegroundColor Green
Write-Host "============================================================`n" -ForegroundColor Cyan

Write-Host "📊 Résumé:" -ForegroundColor Yellow
Write-Host "  - 3 tâches planifiées créées" -ForegroundColor White
Write-Host "  - Email: gonzalefernando@gmail.com" -ForegroundColor White
Write-Host "  - Fréquence: 3x/jour (08:00, 14:00, 20:00)" -ForegroundColor White

Write-Host "`n📧 Prochains rapports automatiques:" -ForegroundColor Yellow
Write-Host "  - Matin: 08:00" -ForegroundColor White
Write-Host "  - Après-midi: 14:00" -ForegroundColor White
Write-Host "  - Soir: 20:00" -ForegroundColor White

Write-Host "`n⚠️  IMPORTANT:" -ForegroundColor Red
Write-Host "  - Ton PC doit rester ALLUMÉ pour que les tâches s'exécutent" -ForegroundColor Yellow
Write-Host "  - Si ton PC est éteint, les tâches ne tourneront PAS" -ForegroundColor Yellow
Write-Host "  - Pour un monitoring 24/7, utilise la solution Cloud Run (deploy-cloud-audit.ps1)" -ForegroundColor Cyan

Write-Host "`n🔗 Ouvrir Task Scheduler:" -ForegroundColor Yellow
Write-Host "  taskschd.msc" -ForegroundColor Cyan

Write-Host "`n✅ Configuration terminée!`n" -ForegroundColor Green
