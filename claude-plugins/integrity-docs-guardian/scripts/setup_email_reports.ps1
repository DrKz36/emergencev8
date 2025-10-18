# ============================================================================
# SETUP EMAIL REPORTS - Configure automated Guardian email reports
# ============================================================================
# This script sets up a Windows Task Scheduler task to send Guardian reports
# by email every 30 minutes
# ============================================================================

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "GUARDIAN EMAIL REPORTS - Configuration des rapports par email" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

# Configuration
$TaskName = "Guardian_EmailReports"
$TaskPath = "\EMERGENCE\"
$RepoRoot = "C:\dev\emergenceV8"
$ScriptDir = "$RepoRoot\claude-plugins\integrity-docs-guardian\scripts"
$PythonScript = "$ScriptDir\send_guardian_reports_email.py"

# Verify Python script exists
if (-not (Test-Path $PythonScript)) {
    Write-Host "ERROR: Script send_guardian_reports_email.py not found at: $PythonScript" -ForegroundColor Red
    exit 1
}

Write-Host "Script found: send_guardian_reports_email.py" -ForegroundColor Green
Write-Host ""

# Find Python executable (prefer venv)
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
Write-Host "  Script: send_guardian_reports_email.py" -ForegroundColor White
Write-Host ""

# Check if task already exists
try {
    $ExistingTask = Get-ScheduledTask -TaskName $TaskName -TaskPath $TaskPath -ErrorAction SilentlyContinue
    if ($ExistingTask) {
        Write-Host "La tache '$TaskName' existe deja." -ForegroundColor Yellow
        Unregister-ScheduledTask -TaskName $TaskName -TaskPath $TaskPath -Confirm:$false
        Write-Host "Tache existante supprimee" -ForegroundColor Green
    }
} catch {
    # Task doesn't exist, continue
}

# Create the action
$Action = New-ScheduledTaskAction -Execute $PythonExe -Argument "`"$PythonScript`"" -WorkingDirectory $RepoRoot

# Create trigger: Repeat every 30 minutes indefinitely
$Trigger1 = New-ScheduledTaskTrigger -Once -At (Get-Date) -RepetitionInterval (New-TimeSpan -Minutes 30)

# Create task settings
$Settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -RunOnlyIfNetworkAvailable `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 5) `
    -RestartCount 3 `
    -RestartInterval (New-TimeSpan -Minutes 1)

# Create principal (run as current user)
$Principal = New-ScheduledTaskPrincipal -UserId "$env:USERDOMAIN\$env:USERNAME" -LogonType S4U

# Register the task
try {
    Register-ScheduledTask `
        -TaskName $TaskName `
        -TaskPath $TaskPath `
        -Action $Action `
        -Trigger $Trigger1 `
        -Settings $Settings `
        -Principal $Principal `
        -Description "Envoi automatique des rapports Guardian par email toutes les 30 minutes"

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

    # Start the task immediately for testing
    Write-Host "Demarrage immediat de la tache pour test..." -ForegroundColor Yellow
    Start-ScheduledTask -TaskName $TaskName -TaskPath $TaskPath
    Write-Host "Tache lancee! Verifiez votre email dans quelques secondes..." -ForegroundColor Green
    Write-Host ""

    Write-Host "Pour gerer la tache:" -ForegroundColor Yellow
    Write-Host "  - Ouvrir: taskschd.msc" -ForegroundColor White
    Write-Host "  - Naviguer vers: Bibliotheque > EMERGENCE > $TaskName" -ForegroundColor White
    Write-Host "  - Ou utiliser: Get-ScheduledTask -TaskName '$TaskName'" -ForegroundColor White
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

Write-Host "Configuration terminee!" -ForegroundColor Green
Write-Host "Les rapports Guardian seront envoyes a: gonzalefernando@gmail.com" -ForegroundColor Cyan
Write-Host ""
