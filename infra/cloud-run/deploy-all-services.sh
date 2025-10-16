#!/bin/bash
# Master deployment script for all Emergence microservices
# Deploys Auth, Session, and Main App services to Cloud Run

set -e

echo "🚀 Emergence Microservices Deployment"
echo "======================================"
echo ""
echo "This script will deploy all Emergence services to Cloud Run:"
echo "  1. Authentication Service"
echo "  2. Session Management Service"
echo "  3. Main Application (optional)"
echo ""

# Configuration
PROJECT_ID="emergence-469005"
REGION="europe-west1"

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

# Function to check if a secret exists
check_secret() {
    local secret_name=$1
    if gcloud secrets describe "$secret_name" --project="$PROJECT_ID" &>/dev/null; then
        return 0
    else
        return 1
    fi
}

# Step 0: Pre-flight checks
echo "🔍 Step 0: Pre-flight checks"
echo "----------------------------"

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    print_error "gcloud CLI not found. Please install Google Cloud SDK."
    exit 1
fi

# Check if docker is installed
if ! command -v docker &> /dev/null; then
    print_error "docker not found. Please install Docker."
    exit 1
fi

# Check if authenticated
if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" &> /dev/null; then
    print_error "Not authenticated with gcloud. Run: gcloud auth login"
    exit 1
fi

# Check project
CURRENT_PROJECT=$(gcloud config get-value project 2>/dev/null)
if [ "$CURRENT_PROJECT" != "$PROJECT_ID" ]; then
    print_warning "Current project is $CURRENT_PROJECT, switching to $PROJECT_ID"
    gcloud config set project "$PROJECT_ID"
fi

print_status "Pre-flight checks passed"
echo ""

# Step 1: Check required secrets
echo "🔐 Step 1: Checking required secrets"
echo "------------------------------------"

REQUIRED_SECRETS=(
    "AUTH_JWT_SECRET"
    "AUTH_ADMIN_EMAILS"
    "OPENAI_API_KEY"
    "ANTHROPIC_API_KEY"
)

MISSING_SECRETS=()
for secret in "${REQUIRED_SECRETS[@]}"; do
    if check_secret "$secret"; then
        print_status "Secret $secret exists"
    else
        MISSING_SECRETS+=("$secret")
        print_error "Secret $secret is missing"
    fi
done

if [ ${#MISSING_SECRETS[@]} -ne 0 ]; then
    print_error "Missing required secrets: ${MISSING_SECRETS[*]}"
    echo ""
    echo "Create missing secrets with:"
    echo "  gcloud secrets create SECRET_NAME --data-file=- --replication-policy=automatic --project=$PROJECT_ID"
    echo ""
    read -p "Do you want to continue anyway? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

echo ""

# Step 2: Deploy Authentication Service
echo "🔐 Step 2: Deploying Authentication Service"
echo "-------------------------------------------"
read -p "Deploy Auth Service? (Y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Nn]$ ]]; then
    if [ -f "infra/cloud-run/deploy-auth-service.sh" ]; then
        chmod +x infra/cloud-run/deploy-auth-service.sh
        ./infra/cloud-run/deploy-auth-service.sh
        print_status "Authentication Service deployed"
    else
        print_error "Auth deployment script not found"
    fi
else
    print_warning "Skipping Auth Service deployment"
fi

echo ""

# Step 3: Deploy Session Service
echo "💬 Step 3: Deploying Session Management Service"
echo "-----------------------------------------------"
read -p "Deploy Session Service? (Y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Nn]$ ]]; then
    if [ -f "infra/cloud-run/deploy-session-service.sh" ]; then
        chmod +x infra/cloud-run/deploy-session-service.sh
        ./infra/cloud-run/deploy-session-service.sh
        print_status "Session Service deployed"
    else
        print_error "Session deployment script not found"
    fi
else
    print_warning "Skipping Session Service deployment"
fi

echo ""

# Step 4: Optional - Deploy Main App
echo "📦 Step 4: Main Application (Optional)"
echo "--------------------------------------"
read -p "Deploy Main Application? (y/N) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    print_warning "Main App deployment not yet automated in this script"
    echo "Use existing deployment method or Skaffold"
else
    print_warning "Skipping Main App deployment"
fi

echo ""

# Step 5: Summary
echo "📊 Step 5: Deployment Summary"
echo "----------------------------"

echo ""
echo "Listing deployed services:"
gcloud run services list --region="$REGION" --project="$PROJECT_ID" --filter="metadata.labels.app=emergence"

echo ""
echo "Service URLs:"
echo ""

# Get Auth Service URL
AUTH_URL=$(gcloud run services describe emergence-auth-service \
    --region="$REGION" \
    --project="$PROJECT_ID" \
    --format="value(status.url)" 2>/dev/null || echo "Not deployed")
echo "🔐 Auth Service:    $AUTH_URL"

# Get Session Service URL
SESSION_URL=$(gcloud run services describe emergence-session-service \
    --region="$REGION" \
    --project="$PROJECT_ID" \
    --format="value(status.url)" 2>/dev/null || echo "Not deployed")
echo "💬 Session Service: $SESSION_URL"

# Get Main App URL
MAIN_URL=$(gcloud run services describe emergence-app \
    --region="$REGION" \
    --project="$PROJECT_ID" \
    --format="value(status.url)" 2>/dev/null || echo "Not deployed")
echo "📦 Main App:        $MAIN_URL"

echo ""
print_status "Deployment complete!"
echo ""
echo "Next steps:"
echo "  1. Test the services using the URLs above"
echo "  2. Configure your frontend to use the new service URLs"
echo "  3. Set up Cloud Load Balancer for unified routing (optional)"
echo "  4. Configure monitoring and alerting"
echo ""
echo "Documentation: infra/cloud-run/MICROSERVICES_ARCHITECTURE.md"
