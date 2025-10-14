# ÉMERGENCE Automatic Rollback Script
# Reverts traffic to previous stable revision after deployment failure
# Projet: emergence-469005
# Région: europe-west1
# Service: emergence-app

param(
    [string]$TargetRevision = "",
    [switch]$Force,
    [switch]$DryRun
)

# Configuration
$PROJECT_ID = "emergence-469005"
$REGION = "europe-west1"
$SERVICE_NAME = "emergence-app"

# Colors for output
function Write-ColorOutput($ForegroundColor) {
    $fc = $host.UI.RawUI.ForegroundColor
    $host.UI.RawUI.ForegroundColor = $ForegroundColor
    if ($args) {
        Write-Output $args
    }
    $host.UI.RawUI.ForegroundColor = $fc
}

function Write-Step($message) {
    Write-ColorOutput Cyan "`n═══════════════════════════════════════════════════════"
    Write-ColorOutput Cyan "  $message"
    Write-ColorOutput Cyan "═══════════════════════════════════════════════════════`n"
}

function Write-Success($message) {
    Write-ColorOutput Green "✅ $message"
}

function Write-Error($message) {
    Write-ColorOutput Red "❌ $message"
}

function Write-Warning($message) {
    Write-ColorOutput Yellow "⚠️  $message"
}

function Write-Info($message) {
    Write-ColorOutput White "ℹ️  $message"
}

# Banner
Write-Host ""
Write-ColorOutput Red "╔════════════════════════════════════════════════════════════════╗"
Write-ColorOutput Red "║                                                                ║"
Write-ColorOutput Red "║              ÉMERGENCE - AUTOMATIC ROLLBACK                    ║"
Write-ColorOutput Red "║                                                                ║"
Write-ColorOutput Red "║   Reverting to previous stable revision                       ║"
Write-ColorOutput Red "║                                                                ║"
Write-ColorOutput Red "╚════════════════════════════════════════════════════════════════╝"
Write-Host ""

if ($DryRun) {
    Write-Warning "DRY RUN MODE - No changes will be made"
    Write-Host ""
}

# ═══════════════════════════════════════════════════════════════════════════════
# Step 1: Get Current Service State
# ═══════════════════════════════════════════════════════════════════════════════
Write-Step "Step 1: Analyzing Current Service State"

Write-Info "Fetching service information..."

# Get current revisions and traffic split
$revisionsJson = gcloud run services describe $SERVICE_NAME `
    --region=$REGION `
    --project=$PROJECT_ID `
    --format=json 2>&1 | ConvertFrom-Json

if ($LASTEXITCODE -ne 0) {
    Write-Error "Failed to fetch service information"
    exit 1
}

# Extract traffic configuration
$traffic = $revisionsJson.status.traffic

Write-Info "Current traffic distribution:"
foreach ($route in $traffic) {
    $percent = $route.percent
    $revision = if ($route.revisionName) { $route.revisionName } else { "LATEST" }
    $tag = if ($route.tag) { " (tag: $($route.tag))" } else { "" }

    Write-Info "  • $percent% → $revision$tag"
}

# ═══════════════════════════════════════════════════════════════════════════════
# Step 2: Identify Rollback Target
# ═══════════════════════════════════════════════════════════════════════════════
Write-Step "Step 2: Identifying Rollback Target"

if ($TargetRevision -ne "") {
    Write-Info "Using specified target revision: $TargetRevision"
    $previousRevision = $TargetRevision
} else {
    Write-Info "Searching for previous stable revision..."

    # List all revisions sorted by creation time
    $allRevisionsJson = gcloud run revisions list `
        --service=$SERVICE_NAME `
        --region=$REGION `
        --project=$PROJECT_ID `
        --format=json `
        --limit=10 2>&1 | ConvertFrom-Json

    if ($LASTEXITCODE -ne 0 -or $allRevisionsJson.Count -eq 0) {
        Write-Error "Failed to list service revisions"
        exit 1
    }

    # Find the current serving revision (highest traffic)
    $currentServing = $traffic | Sort-Object -Property percent -Descending | Select-Object -First 1
    $currentRevisionName = $currentServing.revisionName

    Write-Info "Current serving revision: $currentRevisionName"

    # Find previous active revision (exclude current)
    $previousRevision = $null

    foreach ($rev in $allRevisionsJson) {
        $revName = $rev.metadata.name

        # Skip if it's the current revision
        if ($revName -eq $currentRevisionName) {
            continue
        }

        # Check if revision is in READY state
        $conditions = $rev.status.conditions
        $isReady = $false

        foreach ($condition in $conditions) {
            if ($condition.type -eq "Ready" -and $condition.status -eq "True") {
                $isReady = $true
                break
            }
        }

        if ($isReady) {
            $previousRevision = $revName
            break
        }
    }

    if ($null -eq $previousRevision) {
        Write-Error "No suitable rollback target found"
        Write-Info "Available revisions:"
        foreach ($rev in $allRevisionsJson) {
            Write-Info "  • $($rev.metadata.name) - $($rev.status.conditions | Where-Object { $_.type -eq 'Ready' } | Select-Object -ExpandProperty status)"
        }
        exit 1
    }
}

Write-Success "Rollback target identified: $previousRevision"

# Get target revision details
$targetRevisionJson = gcloud run revisions describe $previousRevision `
    --region=$REGION `
    --project=$PROJECT_ID `
    --format=json 2>&1 | ConvertFrom-Json

if ($LASTEXITCODE -ne 0) {
    Write-Error "Failed to describe target revision: $previousRevision"
    exit 1
}

$targetCreationTime = $targetRevisionJson.metadata.creationTimestamp
$targetImage = $targetRevisionJson.spec.containers[0].image

Write-Info "Target revision details:"
Write-Info "  • Name:    $previousRevision"
Write-Info "  • Created: $targetCreationTime"
Write-Info "  • Image:   $targetImage"

# ═══════════════════════════════════════════════════════════════════════════════
# Step 3: Confirm Rollback
# ═══════════════════════════════════════════════════════════════════════════════
Write-Step "Step 3: Rollback Confirmation"

Write-Warning "You are about to rollback traffic to: $previousRevision"
Write-Warning "This will route 100% of traffic to the previous revision"
Write-Host ""

if (-not $Force -and -not $DryRun) {
    $confirm = Read-Host "Continue with rollback? (y/N)"
    if ($confirm -ne "y" -and $confirm -ne "Y") {
        Write-Warning "Rollback cancelled by user"
        exit 0
    }
}

# ═══════════════════════════════════════════════════════════════════════════════
# Step 4: Execute Rollback
# ═══════════════════════════════════════════════════════════════════════════════
Write-Step "Step 4: Executing Rollback"

if ($DryRun) {
    Write-Info "DRY RUN: Would execute the following command:"
    Write-Info "gcloud run services update-traffic $SERVICE_NAME \"
    Write-Info "  --to-revisions=$previousRevision=100 \"
    Write-Info "  --region=$REGION \"
    Write-Info "  --project=$PROJECT_ID"
    Write-Host ""
    Write-Success "Dry run complete - no changes made"
    exit 0
}

Write-Info "Updating traffic split to 100% → $previousRevision"

gcloud run services update-traffic $SERVICE_NAME `
    --to-revisions="$previousRevision=100" `
    --region=$REGION `
    --project=$PROJECT_ID

if ($LASTEXITCODE -ne 0) {
    Write-Error "Rollback failed"
    exit 1
}

Write-Success "Traffic successfully routed to previous revision"

# ═══════════════════════════════════════════════════════════════════════════════
# Step 5: Verify Rollback
# ═══════════════════════════════════════════════════════════════════════════════
Write-Step "Step 5: Verifying Rollback"

Write-Info "Waiting for rollback to propagate..."
Start-Sleep -Seconds 10

# Test health endpoint
$SERVICE_URL = "https://$SERVICE_NAME-486095406755.$REGION.run.app"

Write-Info "Testing health endpoint: $SERVICE_URL/api/health"

$maxRetries = 5
$retryCount = 0
$healthOk = $false

while ($retryCount -lt $maxRetries) {
    $retryCount++

    try {
        $healthCheck = Invoke-WebRequest -Uri "$SERVICE_URL/api/health" `
            -UseBasicParsing `
            -TimeoutSec 10 `
            -ErrorAction Stop

        if ($healthCheck.StatusCode -eq 200) {
            $healthOk = $true
            Write-Success "Health check passed (HTTP 200)"
            Write-Info "Response: $($healthCheck.Content)"
            break
        }
    } catch {
        Write-Warning "Health check failed (attempt $retryCount/$maxRetries): $_"

        if ($retryCount -lt $maxRetries) {
            Write-Info "Retrying in 10 seconds..."
            Start-Sleep -Seconds 10
        }
    }
}

if (-not $healthOk) {
    Write-Error "Health check failed after rollback"
    Write-Warning "Service may need manual intervention"
    exit 1
}

# Verify traffic distribution
$verifyTrafficJson = gcloud run services describe $SERVICE_NAME `
    --region=$REGION `
    --project=$PROJECT_ID `
    --format=json 2>&1 | ConvertFrom-Json

$verifyTraffic = $verifyTrafficJson.status.traffic

Write-Info "Verified traffic distribution:"
foreach ($route in $verifyTraffic) {
    $percent = $route.percent
    $revision = if ($route.revisionName) { $route.revisionName } else { "LATEST" }
    $tag = if ($route.tag) { " (tag: $($route.tag))" } else { "" }

    if ($revision -eq $previousRevision -and $percent -eq 100) {
        Write-Success "  • $percent% → $revision$tag ✓"
    } else {
        Write-Info "  • $percent% → $revision$tag"
    }
}

# ═══════════════════════════════════════════════════════════════════════════════
# Rollback Complete
# ═══════════════════════════════════════════════════════════════════════════════
Write-Host ""
Write-ColorOutput Green "╔════════════════════════════════════════════════════════════════╗"
Write-ColorOutput Green "║                                                                ║"
Write-ColorOutput Green "║              ✅ ROLLBACK COMPLETE                              ║"
Write-ColorOutput Green "║                                                                ║"
Write-ColorOutput Green "╚════════════════════════════════════════════════════════════════╝"
Write-Host ""

Write-Info "Rollback Summary:"
Write-Info "  Service:          $SERVICE_NAME"
Write-Info "  Active Revision:  $previousRevision"
Write-Info "  Traffic:          100%"
Write-Info "  Status:           🟢 HEALTHY"
Write-Host ""

Write-Info "Next Steps:"
Write-Info "  • Investigate root cause of deployment failure"
Write-Info "  • Check failed revision logs:"
Write-Info "    gcloud run services logs read $SERVICE_NAME --region=$REGION --project=$PROJECT_ID"
Write-Info "  • Review metrics: $SERVICE_URL/api/metrics"
Write-Info "  • Fix issues and redeploy: .\scripts\deploy.ps1"
Write-Host ""

Write-Success "🔄 Rollback successful - service restored to previous stable state"
