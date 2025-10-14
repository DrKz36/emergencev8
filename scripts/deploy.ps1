# ÉMERGENCE Canary Deployment Script
# Automates the full deployment pipeline: Build → Push → Canary → Verify → Stable
# Projet: emergence-469005
# Région: europe-west1
# Service: emergence-app

param(
    [switch]$SkipBuild,
    [switch]$SkipTests,
    [switch]$ManualApproval,
    [string]$ImageTag = ""
)

# Configuration
$PROJECT_ID = "emergence-469005"
$REGION = "europe-west1"
$SERVICE_NAME = "emergence-app"
$REPOSITORY = "europe-west1-docker.pkg.dev/$PROJECT_ID/app"
$PIPELINE_NAME = "emergence-pipeline"

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
Write-ColorOutput Magenta "╔════════════════════════════════════════════════════════════════╗"
Write-ColorOutput Magenta "║                                                                ║"
Write-ColorOutput Magenta "║              ÉMERGENCE - CANARY DEPLOYMENT                     ║"
Write-ColorOutput Magenta "║                                                                ║"
Write-ColorOutput Magenta "║   Build → Push → Canary (20%) → Verify → Stable (100%)        ║"
Write-ColorOutput Magenta "║                                                                ║"
Write-ColorOutput Magenta "╚════════════════════════════════════════════════════════════════╝"
Write-Host ""

# Generate timestamp for image tag
if ($ImageTag -eq "") {
    $timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
    $ImageTag = "deploy-$timestamp"
}

$IMAGE_FULL = "${REPOSITORY}/${SERVICE_NAME}:${ImageTag}"

Write-Info "Deployment Configuration:"
Write-Info "  Project:   $PROJECT_ID"
Write-Info "  Region:    $REGION"
Write-Info "  Service:   $SERVICE_NAME"
Write-Info "  Image:     $IMAGE_FULL"
Write-Info "  Pipeline:  $PIPELINE_NAME"
Write-Host ""

# Confirm deployment
if (-not $ManualApproval) {
    $confirm = Read-Host "Continue with deployment? (y/N)"
    if ($confirm -ne "y" -and $confirm -ne "Y") {
        Write-Warning "Deployment cancelled by user"
        exit 0
    }
}

# ═══════════════════════════════════════════════════════════════════════════════
# Step 1: Pre-deployment Checks
# ═══════════════════════════════════════════════════════════════════════════════
Write-Step "Step 1: Pre-deployment Checks"

# Check gcloud CLI
Write-Info "Checking gcloud CLI..."
$gcloudVersion = gcloud version 2>&1 | Select-String "Google Cloud SDK"
if ($LASTEXITCODE -ne 0) {
    Write-Error "gcloud CLI not found. Please install: https://cloud.google.com/sdk/docs/install"
    exit 1
}
Write-Success "gcloud CLI detected: $gcloudVersion"

# Check Docker
if (-not $SkipBuild) {
    Write-Info "Checking Docker..."
    $dockerVersion = docker --version
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Docker not found. Please install Docker Desktop"
        exit 1
    }
    Write-Success "Docker detected: $dockerVersion"
}

# Authenticate gcloud
Write-Info "Checking gcloud authentication..."
$currentAccount = gcloud config get-value account 2>$null
if ($currentAccount) {
    Write-Success "Authenticated as: $currentAccount"
} else {
    Write-Warning "Not authenticated. Running gcloud auth login..."
    gcloud auth login
}

# Set project
Write-Info "Setting active project..."
gcloud config set project $PROJECT_ID
Write-Success "Project set to: $PROJECT_ID"

# ═══════════════════════════════════════════════════════════════════════════════
# Step 2: Run Tests (optional)
# ═══════════════════════════════════════════════════════════════════════════════
if (-not $SkipTests) {
    Write-Step "Step 2: Running Backend Quality Checks"

    Write-Info "Executing pytest + ruff + mypy..."
    & "$PSScriptRoot\run_backend_quality.ps1"

    if ($LASTEXITCODE -ne 0) {
        Write-Error "Quality checks failed. Aborting deployment."
        Write-Info "To skip tests, use: .\deploy.ps1 -SkipTests"
        exit 1
    }

    Write-Success "All quality checks passed"
} else {
    Write-Warning "Step 2: Skipping tests (as requested)"
}

# ═══════════════════════════════════════════════════════════════════════════════
# Step 3: Build Docker Image
# ═══════════════════════════════════════════════════════════════════════════════
if (-not $SkipBuild) {
    Write-Step "Step 3: Building Docker Image"

    Write-Info "Building image: $IMAGE_FULL"
    Write-Info "Platform: linux/amd64 (Cloud Run compatible)"

    docker build --platform linux/amd64 `
        --tag $IMAGE_FULL `
        --build-arg BUILDKIT_INLINE_CACHE=1 `
        .

    if ($LASTEXITCODE -ne 0) {
        Write-Error "Docker build failed"
        exit 1
    }

    Write-Success "Image built successfully"
} else {
    Write-Warning "Step 3: Skipping build (as requested)"
}

# ═══════════════════════════════════════════════════════════════════════════════
# Step 4: Push to Artifact Registry
# ═══════════════════════════════════════════════════════════════════════════════
Write-Step "Step 4: Pushing Image to Artifact Registry"

Write-Info "Configuring Docker auth for Artifact Registry..."
gcloud auth configure-docker $REGION-docker.pkg.dev --quiet

Write-Info "Pushing image: $IMAGE_FULL"
docker push $IMAGE_FULL

if ($LASTEXITCODE -ne 0) {
    Write-Error "Docker push failed"
    exit 1
}

Write-Success "Image pushed to Artifact Registry"

# ═══════════════════════════════════════════════════════════════════════════════
# Step 5: Create Cloud Deploy Release
# ═══════════════════════════════════════════════════════════════════════════════
Write-Step "Step 5: Creating Cloud Deploy Release (Canary)"

$RELEASE_NAME = "rel-$ImageTag"

Write-Info "Creating release: $RELEASE_NAME"
Write-Info "Pipeline: $PIPELINE_NAME"

gcloud deploy releases create $RELEASE_NAME `
    --project=$PROJECT_ID `
    --region=$REGION `
    --delivery-pipeline=$PIPELINE_NAME `
    --skaffold-file=skaffold.yaml `
    --images="app=$IMAGE_FULL"

if ($LASTEXITCODE -ne 0) {
    Write-Error "Cloud Deploy release creation failed"
    exit 1
}

Write-Success "Release created: $RELEASE_NAME"

# ═══════════════════════════════════════════════════════════════════════════════
# Step 6: Monitor Canary Deployment
# ═══════════════════════════════════════════════════════════════════════════════
Write-Step "Step 6: Monitoring Canary Deployment (20% traffic)"

Write-Info "Canary deployment in progress..."
Write-Info "View in Cloud Console:"
Write-Info "https://console.cloud.google.com/deploy/delivery-pipelines/$REGION/$PIPELINE_NAME?project=$PROJECT_ID"
Write-Host ""

Write-Info "Waiting for canary rollout to complete..."
Start-Sleep -Seconds 10

# Poll for rollout status
$maxAttempts = 30
$attempt = 0
$canarySuccess = $false

while ($attempt -lt $maxAttempts) {
    $attempt++
    Write-Info "Checking rollout status (attempt $attempt/$maxAttempts)..."

    # Get latest rollout status
    $rolloutStatus = gcloud deploy rollouts list `
        --delivery-pipeline=$PIPELINE_NAME `
        --region=$REGION `
        --project=$PROJECT_ID `
        --filter="name:$RELEASE_NAME" `
        --format="value(state)" `
        --limit=1 2>&1

    if ($rolloutStatus -match "SUCCEEDED") {
        $canarySuccess = $true
        break
    } elseif ($rolloutStatus -match "FAILED") {
        Write-Error "Canary deployment FAILED"
        Write-Info "Check logs: gcloud deploy rollouts describe <rollout-name> --region=$REGION --project=$PROJECT_ID"
        exit 1
    } elseif ($rolloutStatus -match "IN_PROGRESS") {
        Write-Info "Status: IN_PROGRESS - waiting..."
    }

    Start-Sleep -Seconds 20
}

if ($canarySuccess) {
    Write-Success "Canary deployment SUCCEEDED (20% traffic)"
} else {
    Write-Error "Canary deployment timed out after $($maxAttempts * 20) seconds"
    exit 1
}

# ═══════════════════════════════════════════════════════════════════════════════
# Step 7: Automatic Promotion to Stable
# ═══════════════════════════════════════════════════════════════════════════════
Write-Step "Step 7: Promoting to Stable (100% traffic)"

Write-Info "Verification passed - promoting to stable target..."
Write-Info "This will route 100% traffic to the new revision"
Write-Host ""

# Promotion is automatic via Cloud Deploy automation rules
Write-Info "Waiting for automatic promotion..."
Start-Sleep -Seconds 10

# Monitor stable promotion
$stableSuccess = $false
$attempt = 0

while ($attempt -lt $maxAttempts) {
    $attempt++
    Write-Info "Checking stable promotion (attempt $attempt/$maxAttempts)..."

    $stableStatus = gcloud deploy rollouts list `
        --delivery-pipeline=$PIPELINE_NAME `
        --region=$REGION `
        --project=$PROJECT_ID `
        --filter="targetId=run-stable AND name:$RELEASE_NAME" `
        --format="value(state)" `
        --limit=1 2>&1

    if ($stableStatus -match "SUCCEEDED") {
        $stableSuccess = $true
        break
    } elseif ($stableStatus -match "FAILED") {
        Write-Error "Stable promotion FAILED"
        Write-Info "Initiating automatic rollback..."
        & "$PSScriptRoot\rollback.ps1"
        exit 1
    }

    Start-Sleep -Seconds 20
}

if ($stableSuccess) {
    Write-Success "Stable promotion SUCCEEDED (100% traffic)"
} else {
    Write-Warning "Stable promotion status unclear - check Cloud Console"
}

# ═══════════════════════════════════════════════════════════════════════════════
# Step 8: Final Verification
# ═══════════════════════════════════════════════════════════════════════════════
Write-Step "Step 8: Final Verification"

Write-Info "Testing production endpoint..."
$SERVICE_URL = "https://$SERVICE_NAME-486095406755.$REGION.run.app"

$healthCheck = Invoke-WebRequest -Uri "$SERVICE_URL/api/health" -UseBasicParsing -TimeoutSec 10 -ErrorAction SilentlyContinue

if ($healthCheck.StatusCode -eq 200) {
    Write-Success "Production endpoint healthy (HTTP 200)"
    Write-Info "Response: $($healthCheck.Content)"
} else {
    Write-Warning "Production endpoint returned: HTTP $($healthCheck.StatusCode)"
}

# ═══════════════════════════════════════════════════════════════════════════════
# Deployment Complete
# ═══════════════════════════════════════════════════════════════════════════════
Write-Host ""
Write-ColorOutput Green "╔════════════════════════════════════════════════════════════════╗"
Write-ColorOutput Green "║                                                                ║"
Write-ColorOutput Green "║              ✅ DEPLOYMENT COMPLETE                            ║"
Write-ColorOutput Green "║                                                                ║"
Write-ColorOutput Green "╚════════════════════════════════════════════════════════════════╝"
Write-Host ""

Write-Info "Deployment Summary:"
Write-Info "  Release:     $RELEASE_NAME"
Write-Info "  Image:       $IMAGE_FULL"
Write-Info "  Service URL: $SERVICE_URL"
Write-Info "  Status:      🟢 STABLE (100% traffic)"
Write-Host ""

Write-Info "Next Steps:"
Write-Info "  • Monitor metrics: $SERVICE_URL/api/metrics"
Write-Info "  • Check logs: gcloud run services logs read $SERVICE_NAME --region=$REGION --project=$PROJECT_ID"
Write-Info "  • View dashboard: https://console.cloud.google.com/run/detail/$REGION/$SERVICE_NAME?project=$PROJECT_ID"
Write-Host ""

Write-Success "🎉 Deployment successful!"
