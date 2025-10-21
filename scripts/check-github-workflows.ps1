# ============================================================
# CHECK GITHUB WORKFLOWS - Polling status sans ouvrir browser
# ============================================================
# Utilise l'API GitHub pour checker le status des workflows
# Sans dépendance à `gh` CLI

param(
    [string]$Branch = "test/github-actions-workflows",
    [int]$MaxChecks = 20,
    [int]$IntervalSeconds = 15
)

$ErrorActionPreference = "Stop"

# Config
$repo = "DrKz36/emergencev8"
$apiUrl = "https://api.github.com/repos/$repo/actions/runs"

Write-Host "`n============================================================" -ForegroundColor Cyan
Write-Host "GITHUB WORKFLOWS STATUS CHECKER" -ForegroundColor Cyan
Write-Host "============================================================`n" -ForegroundColor Cyan
Write-Host "Repository: $repo" -ForegroundColor White
Write-Host "Branch: $Branch" -ForegroundColor White
Write-Host "Max checks: $MaxChecks (every ${IntervalSeconds}s)`n" -ForegroundColor White

function Get-WorkflowRuns {
    try {
        $response = Invoke-RestMethod -Uri "$apiUrl?branch=$Branch&per_page=5" -Headers @{
            "Accept" = "application/vnd.github+json"
            "User-Agent" = "PowerShell-Workflow-Checker"
        }
        return $response.workflow_runs
    }
    catch {
        Write-Host "⚠️  Erreur API GitHub: $($_.Exception.Message)" -ForegroundColor Yellow
        return @()
    }
}

function Format-Status {
    param([string]$status, [string]$conclusion)

    if ($status -eq "completed") {
        switch ($conclusion) {
            "success" { return "✅ SUCCESS", "Green" }
            "failure" { return "❌ FAILURE", "Red" }
            "cancelled" { return "🚫 CANCELLED", "Yellow" }
            default { return "⚠️  $conclusion", "Yellow" }
        }
    }
    elseif ($status -eq "in_progress") {
        return "⏳ IN PROGRESS", "Cyan"
    }
    elseif ($status -eq "queued") {
        return "🕐 QUEUED", "Gray"
    }
    else {
        return "❓ $status", "Gray"
    }
}

function Format-Duration {
    param([datetime]$startTime)
    $elapsed = (Get-Date) - $startTime
    return "{0:mm}m {0:ss}s" -f $elapsed
}

# Polling loop
$checkCount = 0
$previousRuns = @()

while ($checkCount -lt $MaxChecks) {
    $checkCount++

    Write-Host "`n--- Check #$checkCount ---" -ForegroundColor Cyan
    $runs = Get-WorkflowRuns

    if ($runs.Count -eq 0) {
        Write-Host "⚠️  Aucun workflow trouvé pour la branche '$Branch'" -ForegroundColor Yellow
        Start-Sleep -Seconds $IntervalSeconds
        continue
    }

    $allCompleted = $true
    $hasFailure = $false

    foreach ($run in $runs | Select-Object -First 3) {
        $statusText, $color = Format-Status -status $run.status -conclusion $run.conclusion
        $duration = if ($run.status -eq "completed") {
            $start = [datetime]::Parse($run.created_at)
            $end = [datetime]::Parse($run.updated_at)
            $elapsed = $end - $start
            "{0:mm}m {0:ss}s" -f $elapsed
        } else {
            Format-Duration -startTime ([datetime]::Parse($run.created_at))
        }

        Write-Host "`n  $($run.name)" -ForegroundColor White
        Write-Host "    Status: " -NoNewline
        Write-Host $statusText -ForegroundColor $color
        Write-Host "    Duration: $duration" -ForegroundColor Gray
        Write-Host "    Commit: $($run.head_commit.message.Split("`n")[0])" -ForegroundColor Gray

        if ($run.status -ne "completed") {
            $allCompleted = $false
        }
        if ($run.conclusion -eq "failure") {
            $hasFailure = $true
            Write-Host "    Logs: $($run.html_url)" -ForegroundColor Red
        }
    }

    # Si tous les workflows sont terminés, on arrête
    if ($allCompleted) {
        Write-Host "`n============================================================" -ForegroundColor Cyan
        if ($hasFailure) {
            Write-Host "❌ WORKFLOWS TERMINÉS AVEC ÉCHECS" -ForegroundColor Red
            Write-Host "`nOuvre les URLs ci-dessus pour voir les logs détaillés." -ForegroundColor Yellow
            exit 1
        } else {
            Write-Host "✅ TOUS LES WORKFLOWS ONT RÉUSSI !" -ForegroundColor Green
            exit 0
        }
    }

    # Sinon, on continue à poller
    if ($checkCount -lt $MaxChecks) {
        Write-Host "`n⏳ Waiting ${IntervalSeconds}s before next check..." -ForegroundColor Gray
        Start-Sleep -Seconds $IntervalSeconds
    }
}

Write-Host "`n============================================================" -ForegroundColor Cyan
Write-Host "⚠️  Max checks atteint ($MaxChecks). Workflows toujours en cours." -ForegroundColor Yellow
Write-Host "Visite https://github.com/$repo/actions pour voir le statut final." -ForegroundColor White
exit 2
