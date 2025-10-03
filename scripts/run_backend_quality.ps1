param(
    [string[]]$Paths = @('src/backend/features/debate/models.py'),
    [string]$Python = $null,
    [switch]$FailFast = $false
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Resolve-PythonPath([string]$candidate) {
    if ($candidate) {
        return $candidate
    }

    $repoRoot = Split-Path -Parent $PSScriptRoot
    $venvPython = Join-Path $repoRoot '.venv\Scripts\python.exe'
    if (Test-Path $venvPython) {
        return $venvPython
    }

    return 'python'
}

$pythonPath = Resolve-PythonPath $Python

$normalizedPaths = @()
foreach ($pathItem in $Paths) {
    if ([string]::IsNullOrWhiteSpace($pathItem)) {
        continue
    }
    $normalizedPaths += $pathItem.Trim()
}
if ($normalizedPaths.Count -eq 0) {
    throw 'No paths provided for lint/type checks.'
}

$checks = @(
    @{ name = 'ruff';   args = @('-m', 'ruff', 'check') + $normalizedPaths },
    @{ name = 'mypy';   args = @('-m', 'mypy') + $normalizedPaths },
    @{ name = 'pytest'; args = @('-m', 'pytest', 'tests/backend', 'tests/test_benchmarks.py') }
)

$failed = @()

foreach ($check in $checks) {
    Write-Host "=== Running $($check.name) ==="
    & $pythonPath $check.args
    $exitCode = $LASTEXITCODE
    if ($exitCode -ne 0) {
        $failed += "$($check.name) (exit $exitCode)"
        Write-Error "Check $($check.name) failed with exit code $exitCode." -ErrorAction Continue
        if ($FailFast) {
            break
        }
    }
}

if ($failed.Count -gt 0) {
    throw "Quality checks failed: $($failed -join ', ')"
}

Write-Host 'All backend quality checks completed successfully.'


