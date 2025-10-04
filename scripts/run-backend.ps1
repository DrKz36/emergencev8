param(
    [string]$ListenHost = '0.0.0.0',
    [int]$Port = 8000,
    [string]$AppDir = 'src',
    [string]$App = 'backend.main:app',
    [switch]$Reload,
    [string[]]$ExtraArgs = @()
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$repoRoot = Split-Path -Parent $PSScriptRoot
$venvDir = Join-Path $repoRoot '.venv'
$activateScript = Join-Path $venvDir 'Scripts\Activate.ps1'
$pythonExe = $null

Push-Location $repoRoot
try {
    if (Test-Path $activateScript) {
        Write-Host 'Activating virtual environment from .venv...'
        . $activateScript
        $pythonExe = 'python'
    } else {
        $venvPython = Join-Path $venvDir 'Scripts\python.exe'
        if (Test-Path $venvPython) {
            $pythonExe = $venvPython
        } else {
            Write-Warning 'Virtual environment not found; falling back to system python.'
            $pythonExe = 'python'
        }
    }

    $uvicornArgs = @('-m', 'uvicorn', '--app-dir', $AppDir, $App, '--host', $ListenHost, '--port', $Port.ToString())
    if ($Reload) {
        $uvicornArgs += '--reload'
    }
    if ($ExtraArgs.Count -gt 0) {
        $uvicornArgs += $ExtraArgs
    }

    $endpoint = '{0}:{1}' -f $ListenHost, $Port
    Write-Host ("Starting uvicorn ({0}) on {1}..." -f $App, $endpoint) -ForegroundColor Cyan
    Write-Host ("Working directory: {0}" -f $repoRoot) -ForegroundColor DarkGray

    & $pythonExe $uvicornArgs
    $exitCode = $LASTEXITCODE
    if ($exitCode -ne 0) {
        throw "uvicorn exited with code $exitCode"
    }
}
finally {
    Pop-Location
}
