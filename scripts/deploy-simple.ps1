# ÉMERGENCE Simple Deployment Script
# Direct deployment to Cloud Run (100% traffic)
# Simplified version without canary for initial setup
# Projet: emergence-469005
# Région: europe-west1
# Service: emergence-app

param(
    [switch]$SkipBuild,
    [switch]$SkipTests,
    [string]$ImageTag = ""
)

# Configuration
$PROJECT_ID = "emergence-469005"
$REGION = "europe-west1"
$SERVICE_NAME = "emergence-app"
$REPOSITORY = "europe-west1-docker.pkg.dev/$PROJECT_ID/app"

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
Write-ColorOutput Magenta "║         ÉMERGENCE - DIRECT DEPLOYMENT (100%)                   ║"
Write-ColorOutput Magenta "║                                                                ║"
Write-ColorOutput Magenta "║   Build → Push → Deploy                                        ║"
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
Write-Host ""

# Confirm deployment
$confirm = Read-Host "Continue with deployment? (y/N)"
if ($confirm -ne "y" -and $confirm -ne "Y") {
    Write-Warning "Deployment cancelled by user"
    exit 0
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
        Write-Info "To skip tests, use: .\deploy-simple.ps1 -SkipTests"
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
# Step 5: Deploy to Cloud Run (100% traffic)
# ═══════════════════════════════════════════════════════════════════════════════
Write-Step "Step 5: Deploying to Cloud Run (100% traffic)"

Write-Info "Deploying to Cloud Run..."
Write-Info "This will create a new revision and route 100% traffic to it"
Write-Host ""

gcloud run deploy $SERVICE_NAME `
    --image $IMAGE_FULL `
    --platform managed `
    --region $REGION `
    --project $PROJECT_ID `
    --allow-unauthenticated `
    --max-instances 10 `
    --min-instances 1 `
    --cpu 2 `
    --memory 4Gi `
    --timeout 300 `
    --concurrency 80

if ($LASTEXITCODE -ne 0) {
    Write-Error "Cloud Run deployment failed"
    exit 1
}

Write-Success "Cloud Run deployment successful"

# ═══════════════════════════════════════════════════════════════════════════════
# Step 6: Verification
# ═══════════════════════════════════════════════════════════════════════════════
Write-Step "Step 6: Health Verification"

Write-Info "Waiting for service to be ready..."
Start-Sleep -Seconds 15

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
    Write-Error "Health check failed after $maxRetries attempts"
    Write-Warning "Service deployed but may need manual verification"
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
Write-Info "  Image:       $IMAGE_FULL"
Write-Info "  Service URL: $SERVICE_URL"
Write-Info "  Status:      🟢 DEPLOYED (100% traffic)"
Write-Host ""

Write-Info "Next Steps:"
Write-Info "  • Monitor metrics: $SERVICE_URL/api/metrics"
Write-Info "  • Check logs: gcloud run services logs read $SERVICE_NAME --region=$REGION --project=$PROJECT_ID --limit=50"
Write-Info "  • View console: https://console.cloud.google.com/run/detail/$REGION/$SERVICE_NAME?project=$PROJECT_ID"
Write-Host ""

Write-Success "🎉 Deployment successful!"
