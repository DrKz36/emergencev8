[CmdletBinding()]
param(
    [string]$PythonPath = "python",
    [string]$BaseUrl = "https://emergence-app-47nct44nma-ew.a.run.app",
    [string]$LoginEmail,
    [string]$LoginPassword,
    [string]$Agent = "anima",
    [switch]$SkipTimeline,
    [switch]$SkipMetrics,
    [switch]$SkipTests,
    [switch]$TriggerMemory,
    [switch]$UseRag,
    [switch]$RunCleanup
)

Set-StrictMode -Version Latest
try { [Console]::OutputEncoding = [System.Text.Encoding]::UTF8 } catch {}
$ErrorActionPreference = "Stop"

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")
Push-Location $repoRoot
try {
    Write-Host "=== [QA] Combined cockpit validation ==="
    $qaArgs = @("qa_metrics_validation.py", "--base-url", $BaseUrl)
    if ($LoginEmail) {
        $qaArgs += @("--login-email", $LoginEmail)
    }
    if ($LoginPassword) {
        $qaArgs += @("--login-password", $LoginPassword)
    }
    if ($SkipTimeline) {
        $qaArgs += "--skip-timeline"
    }
    if ($SkipMetrics) {
        $qaArgs += "--skip-metrics"
    }
    if ($TriggerMemory) {
        $qaArgs += "--trigger-memory"
    }
    if ($UseRag) {
        $qaArgs += "--use-rag"
    }
    $qaArgs += @("--agent", $Agent)

    Write-Host ">> $PythonPath $($qaArgs -join ' ')"
    & $PythonPath @qaArgs
    if ($LASTEXITCODE -ne 0) {
        Write-Warning ("qa_metrics_validation.py exited with code {0}" -f $LASTEXITCODE)
    }

    if (-not $SkipTests) {
        Write-Host "`n=== [QA] PowerShell smoke suite ==="
        $testArgs = @("-File", "tests/run_all.ps1", "-BaseUrl", $BaseUrl)
        if ($LoginEmail) {
            $testArgs += @("-SmokeEmail", $LoginEmail)
        }
        if ($LoginPassword) {
            $testArgs += @("-SmokePassword", $LoginPassword)
        }
        Write-Host ">> pwsh $($testArgs -join ' ')"
        & pwsh.exe @testArgs
        if ($LASTEXITCODE -ne 0) {
            Write-Warning ("tests/run_all.ps1 exited with code {0}" -f $LASTEXITCODE)
        }
    }

    if ($RunCleanup) {
        Write-Host "`n=== [QA] Cleanup artefacts ==="
        $cleanupArgs = @("scripts/qa/purge_test_documents.py", "--base-url", $BaseUrl)
        if ($LoginEmail) {
            $cleanupArgs += @("--login-email", $LoginEmail)
        }
        if ($LoginPassword) {
            $cleanupArgs += @("--login-password", $LoginPassword)
        }
        Write-Host ">> $PythonPath $($cleanupArgs -join ' ')"
        & $PythonPath @cleanupArgs
        if ($LASTEXITCODE -ne 0) {
            Write-Warning ("Cleanup script exited with code {0}" -f $LASTEXITCODE)
        }
    }
} finally {
    Pop-Location
}
