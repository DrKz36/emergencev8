#requires -Version 5.1
<#
.SYNOPSIS
    Compatibility wrapper that delegates to run-vector-store-reset.ps1.
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

$delegateScript = Join-Path (Split-Path -Parent $MyInvocation.MyCommand.Path) 'run-vector-store-reset.ps1'
if (-not (Test-Path $delegateScript)) {
    throw "run-vector-store-reset.ps1 introuvable (chemin: $delegateScript)"
}

$invokeParams = @{}
foreach ($pair in $PSBoundParameters.GetEnumerator()) {
    $invokeParams[$pair.Key] = $pair.Value
}

& $delegateScript @invokeParams
