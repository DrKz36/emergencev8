# Setup Archive Guardian - Automated Cleanup Scheduler
# Creates a Windows Scheduled Task to run archive_guardian.py weekly

param(
    [switch]$Remove,
    [switch]$Status
)

$TaskName = "EmergenceArchiveGuardian"
$ScriptPath = Join-Path $PSScriptRoot "archive_guardian.py"
$RepoRoot = Split-Path (Split-Path (Split-Path $PSScriptRoot -Parent) -Parent) -Parent
$PythonExe = Join-Path $RepoRoot ".venv\Scripts\python.exe"

# Check if Python exists
if (-not (Test-Path $PythonExe)) {
    Write-Host "[ERROR] Python not found at: $PythonExe" -ForegroundColor Red
    Write-Host "[INFO] Please activate virtual environment first" -ForegroundColor Yellow
    exit 1
}

# Check if script exists
if (-not (Test-Path $ScriptPath)) {
    Write-Host "[ERROR] Script not found at: $ScriptPath" -ForegroundColor Red
    exit 1
}

# Function to check task status
function Get-TaskStatus {
    $task = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue

    if ($null -eq $task) {
        Write-Host "`n[STATUS] Archive Guardian Scheduler: NOT CONFIGURED" -ForegroundColor Yellow
        Write-Host "[INFO] Run this script without parameters to setup" -ForegroundColor Cyan
        return $false
    }

    Write-Host "`n=== ARCHIVE GUARDIAN SCHEDULER STATUS ===" -ForegroundColor Green
    Write-Host "Task Name: $TaskName"
    Write-Host "State: $($task.State)"
    Write-Host "Last Run: $($task | Get-ScheduledTaskInfo | Select-Object -ExpandProperty LastRunTime)"
    Write-Host "Next Run: $($task | Get-ScheduledTaskInfo | Select-Object -ExpandProperty NextRunTime)"
    Write-Host "Last Result: $($task | Get-ScheduledTaskInfo | Select-Object -ExpandProperty LastTaskResult)"
    Write-Host ""

    # Show trigger details
    $trigger = $task.Triggers[0]
    Write-Host "Schedule: Every $($trigger.DaysInterval) day(s) at $($trigger.StartBoundary.ToString('HH:mm'))"
    Write-Host "Script: $ScriptPath"
    Write-Host "Python: $PythonExe"
    Write-Host ""

    return $true
}

# Function to remove task
function Remove-ArchiveTask {
    Write-Host "`n[REMOVE] Removing Archive Guardian Scheduler..." -ForegroundColor Yellow

    $task = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue

    if ($null -eq $task) {
        Write-Host "[INFO] Task not found. Nothing to remove." -ForegroundColor Cyan
        return
    }

    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
    Write-Host "[OK] Archive Guardian Scheduler removed successfully!" -ForegroundColor Green
}

# Function to create task
function New-ArchiveTask {
    Write-Host "`n=== SETUP ARCHIVE GUARDIAN SCHEDULER ===" -ForegroundColor Green
    Write-Host ""

    # Check if task already exists
    $existingTask = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue

    if ($null -ne $existingTask) {
        Write-Host "[WARNING] Task '$TaskName' already exists!" -ForegroundColor Yellow
        $response = Read-Host "Do you want to remove and recreate it? (yes/no)"

        if ($response -ne "yes") {
            Write-Host "[CANCELLED] Setup cancelled." -ForegroundColor Yellow
            return
        }

        Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
        Write-Host "[OK] Existing task removed." -ForegroundColor Green
    }

    # Task configuration
    $action = New-ScheduledTaskAction `
        -Execute $PythonExe `
        -Argument "`"$ScriptPath`" --auto" `
        -WorkingDirectory $RepoRoot

    # Trigger: Every Sunday at 3:00 AM
    $trigger = New-ScheduledTaskTrigger `
        -Weekly `
        -DaysOfWeek Sunday `
        -At 3:00AM

    # Settings
    $settings = New-ScheduledTaskSettingsSet `
        -AllowStartIfOnBatteries `
        -DontStopIfGoingOnBatteries `
        -StartWhenAvailable `
        -RunOnlyIfNetworkAvailable:$false

    # Principal (run as current user)
    $principal = New-ScheduledTaskPrincipal `
        -UserId $env:USERNAME `
        -LogonType Interactive `
        -RunLevel Highest

    # Register task
    $task = Register-ScheduledTask `
        -TaskName $TaskName `
        -Action $action `
        -Trigger $trigger `
        -Settings $settings `
        -Principal $principal `
        -Description "ANIMA Archive Guardian - Automated cleanup of obsolete files in repository root (runs weekly)"

    Write-Host ""
    Write-Host "[OK] Archive Guardian Scheduler created successfully!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Configuration:" -ForegroundColor Cyan
    Write-Host "  - Task Name: $TaskName"
    Write-Host "  - Schedule: Every Sunday at 3:00 AM"
    Write-Host "  - Script: $ScriptPath"
    Write-Host "  - Python: $PythonExe"
    Write-Host "  - Mode: Automatic (--auto flag)"
    Write-Host ""
    Write-Host "Next Steps:" -ForegroundColor Yellow
    Write-Host "  - Task will run automatically every Sunday"
    Write-Host "  - Check status: .\setup_archive_scheduler.ps1 -Status"
    Write-Host "  - View reports: reports/archive_cleanup_report.json"
    Write-Host "  - Manual run: python claude-plugins/integrity-docs-guardian/scripts/archive_guardian.py --auto"
    Write-Host ""
}

# Main logic
if ($Remove) {
    Remove-ArchiveTask
}
elseif ($Status) {
    Get-TaskStatus
}
else {
    New-ArchiveTask
}
