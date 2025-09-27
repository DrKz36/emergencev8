#requires -Version 5.1
<#!
.SYNOPSIS
    QA helper scenario to validate the memory:clear workflow end-to-end.
.DESCRIPTION
    Runs a quick API health check, executes the detailed automated test located in tests/test_memory_clear.ps1,
    and prints the manual UI verifications expected from the QA checklist.
    Execute from the repository root.
!>
[CmdletBinding()]
param(
    [string]$BaseUrl = "http://127.0.0.1:8000",
    [string]$AuthToken = $env:EMERGENCE_ID_TOKEN,
    [string]$SessionId,
    [switch]$SkipHealthCheck,
    [switch]$SkipAutomatedTest,
    [switch]$Silent
)

$ErrorActionPreference = "Stop"
try { [Console]::OutputEncoding = [System.Text.Encoding]::UTF8 } catch {}
$PSDefaultParameterValues['Out-File:Encoding'] = 'utf8'

function Write-ScenarioNote {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Message
    )
    Write-Host "#<- $Message" -ForegroundColor DarkGray
}

if (-not $SessionId -or -not $SessionId.Trim()) {
    $SessionId = "memclr-" + ([Guid]::NewGuid().ToString("N"))
} else {
    $SessionId = $SessionId.Trim()
}

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..' '..')).Path
$testScript = Join-Path $repoRoot 'tests/test_memory_clear.ps1'

if (-not (Test-Path $testScript)) {
    throw "Cannot locate tests/test_memory_clear.ps1 under $repoRoot"
}

Write-Host "=== memory:clear QA scenario ===" -ForegroundColor Green
Write-Host "Repo root     : $repoRoot"
Write-Host "API base URL  : $BaseUrl"
if ($AuthToken) {
    Write-Host "Auth token    : provided (env/param)" -ForegroundColor DarkGray
} else {
    Write-Host "Auth token    : none (dev mode expected)" -ForegroundColor Yellow
}
Write-Host "Session ID    : $SessionId"
Write-ScenarioNote ("session-id=" + $SessionId)

Write-ScenarioNote "Step 1: Health check"
if (-not $SkipHealthCheck) {
    Write-Host "`n[1] Health-check $BaseUrl/api/health" -ForegroundColor Cyan
    try {
        $health = Invoke-RestMethod -Method Get -Uri ("{0}/api/health" -f $BaseUrl.TrimEnd('/')) -TimeoutSec 10
        if ($null -eq $health) {
            Write-Warning "Health endpoint responded with empty payload."
        } else {
            Write-Host (ConvertTo-Json $health -Depth 4)
        }
    } catch {
        Write-Error "Health-check failed: $($_.Exception.Message)"
        throw
    }
} else {
    Write-Host "`n[1] Health-check skipped." -ForegroundColor DarkGray
}

Write-ScenarioNote "Step 2: Automated coverage"
if (-not $SkipAutomatedTest) {
    Write-Host "`n[2] Running automated coverage (tests/test_memory_clear.ps1)" -ForegroundColor Cyan
    $pwshExe = (Get-Command pwsh -ErrorAction SilentlyContinue)?.Path
    if (-not $pwshExe) {
        $pwshExe = (Get-Command powershell -ErrorAction SilentlyContinue)?.Path
    }
    if (-not $pwshExe) {
        throw "Neither pwsh nor Windows PowerShell found in PATH."
    }

    $invokeParams = @{
        FilePath = $pwshExe
        ArgumentList = @('-ExecutionPolicy','Bypass','-File',$testScript,'-BaseUrl',$BaseUrl)
        NoNewWindow = $true
        Wait = $true
        PassThru = $true
    }

    if ($SessionId) {
        $invokeParams.ArgumentList += @('-SessionId', $SessionId)
    }
    if ($AuthToken) {
        $invokeParams.ArgumentList += @('-AuthToken', $AuthToken)
    }

    $process = Start-Process @invokeParams
    if ($process.ExitCode -ne 0) {
        throw "Automated memory:clear test failed (exit code $($process.ExitCode))."
    }
} else {
    Write-Host "`n[2] Automated coverage skipped." -ForegroundColor DarkGray
}

if (-not $Silent) {
    Write-Host "`n[3] Manual QA checklist" -ForegroundColor Cyan
    Write-ScenarioNote "Manual: Open the frontend, sign in, and pick an existing thread."
    Write-ScenarioNote "Manual: Confirm the memory banner shows counts before the purge."
    Write-ScenarioNote "Manual: Click Clear, validate the confirmation modal, confirm the success toast."
    Write-ScenarioNote "Manual: Refresh and ensure STM/LTM indicators are empty."
    Write-ScenarioNote "Manual: Log the run in docs/Memoire.md (journal / QA section)."
}

Write-ScenarioNote "Scenario completed"
Write-Host "`n=== Done. memory:clear scenario completed ===" -ForegroundColor Green
