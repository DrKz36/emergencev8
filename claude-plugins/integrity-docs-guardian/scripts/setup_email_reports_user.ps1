# ============================================================================
# SETUP EMAIL REPORTS (USER MODE) - Configure automated Guardian email reports
# ============================================================================
# This version runs without admin rights
# ============================================================================

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "GUARDIAN EMAIL REPORTS - Configuration (Mode Utilisateur)" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

# Configuration
$TaskName = "Guardian_EmailReports"
$RepoRoot = "C:\dev\emergenceV8"
$ScriptDir = "$RepoRoot\claude-plugins\integrity-docs-guardian\scripts"
$PythonScript = "$ScriptDir\send_guardian_reports_email.py"

# Verify Python script exists
if (-not (Test-Path $PythonScript)) {
    Write-Host "ERROR: Script send_guardian_reports_email.py not found" -ForegroundColor Red
    exit 1
}

# Find Python executable (prefer venv)
$PythonExe = $null
if (Test-Path "$RepoRoot\.venv\Scripts\python.exe") {
    $PythonExe = "$RepoRoot\.venv\Scripts\python.exe"
} else {
    $PythonCmd = Get-Command python -ErrorAction SilentlyContinue
    if ($PythonCmd) {
        $PythonExe = $PythonCmd.Source
    } else {
        Write-Host "ERROR: Python not found!" -ForegroundColor Red
        exit 1
    }
}

Write-Host "Script found: send_guardian_reports_email.py" -ForegroundColor Green
Write-Host "Python: $PythonExe" -ForegroundColor Green
Write-Host ""

# Check if task already exists
try {
    $ExistingTask = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
    if ($ExistingTask) {
        Write-Host "La tache '$TaskName' existe deja - suppression..." -ForegroundColor Yellow
        Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
        Write-Host "Tache existante supprimee" -ForegroundColor Green
    }
} catch {
    # Task doesn't exist, continue
}

Write-Host "Creation de la tache planifiee..." -ForegroundColor Yellow
Write-Host ""

# Create the action
$Action = New-ScheduledTaskAction -Execute $PythonExe -Argument "`"$PythonScript`"" -WorkingDirectory $RepoRoot

# Create trigger: Repeat every 30 minutes
$Trigger = New-ScheduledTaskTrigger -Once -At (Get-Date) -RepetitionInterval (New-TimeSpan -Minutes 30)

# Create task settings
$Settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -RunOnlyIfNetworkAvailable `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 5)

# Register the task (user-level, no admin needed)
try {
    Register-ScheduledTask `
        -TaskName $TaskName `
        -Action $Action `
        -Trigger $Trigger `
        -Settings $Settings `
        -Description "Envoi automatique des rapports Guardian par email toutes les 30 minutes" `
        -Force

    Write-Host "SUCCESS: Tache planifiee creee avec succes!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Details:" -ForegroundColor Cyan
    Write-Host "  Nom: $TaskName" -ForegroundColor White
    Write-Host "  Frequence: Toutes les 30 minutes" -ForegroundColor White
    Write-Host "  Email: gonzalefernando@gmail.com" -ForegroundColor White
    Write-Host ""

    # Start the task immediately for testing
    Write-Host "Test immediat - envoi d'un email..." -ForegroundColor Yellow
    Start-ScheduledTask -TaskName $TaskName
    Write-Host "Email envoye! Verifiez votre boite mail." -ForegroundColor Green
    Write-Host ""

    # Show next run time
    $Task = Get-ScheduledTask -TaskName $TaskName
    $Info = Get-ScheduledTaskInfo -TaskName $TaskName
    Write-Host "Prochaine execution: Dans 30 minutes" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Pour gerer la tache: Get-ScheduledTask -TaskName '$TaskName'" -ForegroundColor Yellow
    Write-Host ""

} catch {
    Write-Host ""
    Write-Host "ERROR: Impossible de creer la tache" -ForegroundColor Red
    Write-Host "Message: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

Write-Host "Configuration terminee!" -ForegroundColor Green
