#requires -Version 5.1
<#
.SYNOPSIS
    Runs the vector store reset scenario with automatic backend lifecycle management.
.DESCRIPTION
    Delegates the full scenario to tests/test_vector_store_reset.ps1 using its -AutoBackend option
    and archives the console output under docs/assets/memoire for weekly tracking.
#>
[CmdletBinding()]
param(
    [string]$RepoRoot,
    [string]$LogDirectory = 'docs/assets/memoire',
    [string]$LogPrefix = 'vector-store-reset',
    [string]$BackendHost = '127.0.0.1',
    [int]$BackendPort = 8000,
    [int]$BackendStartupTimeoutSec = 60,
    [switch]$Quiet
)

$ErrorActionPreference = 'Stop'
try { [Console]::OutputEncoding = [System.Text.Encoding]::UTF8 } catch {}
$PSDefaultParameterValues['Out-File:Encoding'] = 'utf8'

if (-not $RepoRoot) {
    $RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..' '..')).Path
}

if (-not [System.IO.Path]::IsPathRooted($LogDirectory)) {
    $LogDirectory = Join-Path $RepoRoot $LogDirectory
}

if (-not (Test-Path $LogDirectory)) {
    New-Item -ItemType Directory -Path $LogDirectory -Force | Out-Null
}

$testScript = Join-Path $RepoRoot 'tests/test_vector_store_reset.ps1'
if (-not (Test-Path $testScript)) {
    throw "tests/test_vector_store_reset.ps1 introuvable depuis $RepoRoot"
}

$timestamp = Get-Date -Format 'yyyyMMdd'
$logName = '{0}-{1}.log' -f $LogPrefix, $timestamp
$logPath = Join-Path $LogDirectory $logName
if (Test-Path $logPath) {
    $timestamp = Get-Date -Format 'yyyyMMdd-HHmmss'
    $logName = '{0}-{1}.log' -f $LogPrefix, $timestamp
    $logPath = Join-Path $LogDirectory $logName
}

$invokeParams = @{
    AutoBackend = $true
    BackendHost = $BackendHost
    BackendPort = $BackendPort
    BackendStartupTimeoutSec = $BackendStartupTimeoutSec
}

Push-Location $RepoRoot
$transcriptStarted = $false
try {
    Start-Transcript -Path $logPath -Force | Out-Null
    $transcriptStarted = $true
    & $testScript @invokeParams
    if (-not $Quiet) {
        Write-Host "Log archive : $logPath" -ForegroundColor Cyan
    }
}
catch {
    if (-not $Quiet) {
        Write-Host "Echec du scenario (voir $logPath)" -ForegroundColor Red
    }
    throw
}
finally {
    if ($transcriptStarted) {
        Stop-Transcript | Out-Null
    }
    Pop-Location
}
