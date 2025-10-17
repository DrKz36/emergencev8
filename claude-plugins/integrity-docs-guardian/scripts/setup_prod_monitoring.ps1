# ============================================================================
# SETUP PROD MONITORING - Configure automated production monitoring
# ============================================================================
# This script sets up a Windows Task Scheduler task to run check_prod_logs.py
# every 30 minutes to monitor the emergence-app on Google Cloud Run
# ============================================================================

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "PROD GUARDIAN - Configuration de la surveillance automatique" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

# Configuration
$TaskName = "ProdGuardian_AutoMonitor"
$TaskPath = "\EMERGENCE\"
$RepoRoot = "C:\dev\emergenceV8"
$ScriptDir = "$RepoRoot\claude-plugins\integrity-docs-guardian\scripts"
$PythonScript = "$ScriptDir\check_prod_logs.py"

# Verify Python script exists
if (-not (Test-Path $PythonScript)) {
    Write-Host "ERROR: Script check_prod_logs.py not found at: $PythonScript" -ForegroundColor Red
    exit 1
}

Write-Host "Script found: check_prod_logs.py" -ForegroundColor Green
Write-Host ""

# Find Python executable
$PythonExe = $null
if (Test-Path "$RepoRoot\.venv\Scripts\python.exe") {
    $PythonExe = "$RepoRoot\.venv\Scripts\python.exe"
    Write-Host "Python found in venv: $PythonExe" -ForegroundColor Green
} else {
    $PythonCmd = Get-Command python -ErrorAction SilentlyContinue
    if ($PythonCmd) {
        $PythonExe = $PythonCmd.Source
        Write-Host "Python found: $PythonExe" -ForegroundColor Green
    } else {
        Write-Host "ERROR: Python not found!" -ForegroundColor Red
        exit 1
    }
}

Write-Host ""
Write-Host "Configuration de la tache planifiee..." -ForegroundColor Yellow
Write-Host "  Nom: $TaskName" -ForegroundColor White
Write-Host "  Frequence: Toutes les 30 minutes" -ForegroundColor White
Write-Host "  Script: check_prod_logs.py" -ForegroundColor White
Write-Host ""

# Check if task already exists
try {
    $ExistingTask = Get-ScheduledTask -TaskName $TaskName -TaskPath $TaskPath -ErrorAction SilentlyContinue
    if ($ExistingTask) {
        Write-Host "La tache '$TaskName' existe deja." -ForegroundColor Yellow
        $Response = Read-Host "Voulez-vous la recreer? (O/N)"
        if ($Response -ne "O") {
            Write-Host "Configuration annulee." -ForegroundColor Yellow
            exit 0
        }
        Unregister-ScheduledTask -TaskName $TaskName -TaskPath $TaskPath -Confirm:$false
        Write-Host "Tache existante supprimee" -ForegroundColor Green
    }
} catch {
    # Task doesn't exist, continue
}

# Create the action
$Action = New-ScheduledTaskAction -Execute $PythonExe -Argument "`"$PythonScript`"" -WorkingDirectory $ScriptDir

# Create the trigger (every 30 minutes, indefinitely)
$Trigger = New-ScheduledTaskTrigger -Once -At (Get-Date) -RepetitionInterval (New-TimeSpan -Minutes 30)

# Create task settings
$Settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -RunOnlyIfNetworkAvailable `
    -ExecutionTimeLimit (New-TimeSpan -Hours 1)

# Create principal (run as current user)
$Principal = New-ScheduledTaskPrincipal -UserId "$env:USERDOMAIN\$env:USERNAME" -LogonType Interactive

# Register the task
try {
    Register-ScheduledTask `
        -TaskName $TaskName `
        -TaskPath $TaskPath `
        -Action $Action `
        -Trigger $Trigger `
        -Settings $Settings `
        -Principal $Principal `
        -Description "Surveillance automatique de la production EMERGENCE sur Google Cloud toutes les 30 minutes"

    Write-Host ""
    Write-Host "SUCCESS: Tache planifiee creee avec succes!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Details de la tache:" -ForegroundColor Cyan
    Write-Host "  Nom: $TaskName" -ForegroundColor White
    Write-Host "  Chemin: $TaskPath" -ForegroundColor White
    Write-Host "  Frequence: Toutes les 30 minutes" -ForegroundColor White
    Write-Host "  Python: $PythonExe" -ForegroundColor White
    Write-Host "  Script: $PythonScript" -ForegroundColor White
    Write-Host ""
    Write-Host "Pour gerer la tache:" -ForegroundColor Yellow
    Write-Host "  - Ouvrir: taskschd.msc" -ForegroundColor White
    Write-Host "  - Naviguer vers: Bibliotheque > EMERGENCE" -ForegroundColor White
    Write-Host "  - Ou utiliser: Get-ScheduledTask -TaskName '$TaskName'" -ForegroundColor White
    Write-Host ""
    Write-Host "Pour tester maintenant:" -ForegroundColor Yellow
    Write-Host "  Start-ScheduledTask -TaskName '$TaskName' -TaskPath '$TaskPath'" -ForegroundColor White
    Write-Host ""

} catch {
    Write-Host ""
    Write-Host "ERROR: Impossible de creer la tache planifiee" -ForegroundColor Red
    Write-Host "Message: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host ""
    Write-Host "Note: Vous devez peut-etre executer PowerShell en tant qu'administrateur" -ForegroundColor Yellow
    Write-Host ""
    exit 1
}

# Test the task immediately
Write-Host "Voulez-vous tester la tache maintenant? (O/N)" -ForegroundColor Yellow
$TestResponse = Read-Host
if ($TestResponse -eq "O") {
    Write-Host ""
    Write-Host "Execution de la tache de test..." -ForegroundColor Yellow
    Start-ScheduledTask -TaskName $TaskName -TaskPath $TaskPath
    Write-Host "Tache lancee! Consultez les rapports dans: $ScriptDir\..\reports\" -ForegroundColor Green
    Write-Host ""
}

Write-Host "Configuration terminee!" -ForegroundColor Green
