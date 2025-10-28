# ============================================================================
# GUARDIAN MONITOR WITH NOTIFICATIONS
# ============================================================================
# Execute ProdGuardian et envoie notifications Windows si problèmes détectés
# Utilisé par Task Scheduler pour monitoring continu
# ============================================================================

param(
    [Parameter(Mandatory=$false)]
    [string]$EmailTo = ""
)

$ErrorActionPreference = "Stop"
$repoRoot = "C:\dev\emergenceV8"
$scriptsDir = "$repoRoot\claude-plugins\integrity-docs-guardian\scripts"
$reportsDir = "$repoRoot\reports"

# Change to repo root
Set-Location $repoRoot

Write-Host "🛡️  Guardian Monitor - Starting production check..." -ForegroundColor Cyan
Write-Host "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')" -ForegroundColor Gray
Write-Host ""

# Execute ProdGuardian
Write-Host "☁️  Checking production health..." -ForegroundColor White
$prodResult = & python "$scriptsDir\check_prod_logs.py" 2>&1
$prodExitCode = $LASTEXITCODE

# Lire le rapport JSON
$prodReportPath = "$reportsDir\prod_report.json"
if (Test-Path $prodReportPath) {
    $prodReport = Get-Content $prodReportPath -Raw | ConvertFrom-Json

    $status = $prodReport.status
    $issuesCount = $prodReport.statistics.issues_found

    Write-Host "Status: $status" -ForegroundColor $(if ($status -eq "ok") { "Green" } elseif ($status -eq "warning") { "Yellow" } else { "Red" })
    Write-Host "Issues found: $issuesCount" -ForegroundColor Gray
    Write-Host ""

    # Envoyer notification si problèmes détectés
    if ($status -eq "critical" -or $issuesCount -gt 0) {
        $title = "Guardian Production Alert"
        $message = "$issuesCount issue(s) detected in production"

        if ($status -eq "critical") {
            $severity = "critical"
            $message += " (CRITICAL)"
        } elseif ($status -eq "warning") {
            $severity = "warning"
        } else {
            $severity = "info"
        }

        # Toast notification
        Write-Host "📢 Sending notification..." -ForegroundColor Yellow
        & pwsh -File "$scriptsDir\send_toast_notification.ps1" `
            -Title $title `
            -Message $message `
            -Severity $severity `
            -ReportPath $prodReportPath

        # Email notification (si configuré)
        if ($EmailTo) {
            Write-Host "📧 Sending email to $EmailTo..." -ForegroundColor Yellow
            & python "$scriptsDir\send_guardian_reports_email.py" --to $EmailTo
        }
    } else {
        Write-Host "✅ Production is healthy - no notification needed" -ForegroundColor Green
    }
} else {
    Write-Host "⚠️  Production report not found - skipping notifications" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "✅ Guardian Monitor completed" -ForegroundColor Green
exit $prodExitCode
