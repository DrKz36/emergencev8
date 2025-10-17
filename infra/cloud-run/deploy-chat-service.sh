#!/bin/bash
# Deploy script for Emergence Chat/LLM Service (P2.4)
# Usage: ./deploy-chat-service.sh [--build-only|--deploy-only]

set -e  # Exit on error

PROJECT_ID="emergence-469005"
REGION="europe-west1"
SERVICE_NAME="emergence-chat-service"
IMAGE_NAME="emergence-chat-service"
DOCKERFILE="chat-service.Dockerfile"
YAML_FILE="chat-service.yaml"

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/../.." && pwd )"

echo "========================================="
echo "  Emergence Chat/LLM Service Deploy"
echo "========================================="
echo "Project ID: $PROJECT_ID"
echo "Region: $REGION"
echo "Service: $SERVICE_NAME"
echo "========================================="
echo ""

# Parse arguments
BUILD_ONLY=false
DEPLOY_ONLY=false
if [[ "$1" == "--build-only" ]]; then
  BUILD_ONLY=true
elif [[ "$1" == "--deploy-only" ]]; then
  DEPLOY_ONLY=true
fi

# ========== BUILD ==========
if [[ "$DEPLOY_ONLY" == false ]]; then
  echo "📦 Step 1/3: Building Docker image..."
  cd "$PROJECT_ROOT"

  # Build with Cloud Build (faster, recommended)
  echo "Building with Cloud Build..."
  gcloud builds submit \
    --project="$PROJECT_ID" \
    --config=- \
    --substitutions=_IMAGE_NAME="$IMAGE_NAME" \
    . <<EOF
steps:
- name: 'gcr.io/cloud-builders/docker'
  args:
  - 'build'
  - '-f'
  - 'infra/cloud-run/$DOCKERFILE'
  - '-t'
  - 'europe-west1-docker.pkg.dev/$PROJECT_ID/app/$IMAGE_NAME:latest'
  - '-t'
  - 'europe-west1-docker.pkg.dev/$PROJECT_ID/app/$IMAGE_NAME:\$BUILD_ID'
  - '.'
images:
- 'europe-west1-docker.pkg.dev/$PROJECT_ID/app/$IMAGE_NAME:latest'
- 'europe-west1-docker.pkg.dev/$PROJECT_ID/app/$IMAGE_NAME:\$BUILD_ID'
timeout: 900s
EOF

  echo "✅ Docker image built and pushed!"
  echo ""
fi

if [[ "$BUILD_ONLY" == true ]]; then
  echo "🚀 Build complete! (--build-only specified)"
  exit 0
fi

# ========== PRE-DEPLOY CHECKS ==========
echo "🔍 Step 2/3: Pre-deployment checks..."

# Check secrets exist
echo "Checking required secrets..."
REQUIRED_SECRETS=("OPENAI_API_KEY" "ANTHROPIC_API_KEY")
MISSING_SECRETS=()

for SECRET in "${REQUIRED_SECRETS[@]}"; do
  if ! gcloud secrets describe "$SECRET" --project="$PROJECT_ID" &>/dev/null; then
    MISSING_SECRETS+=("$SECRET")
  fi
done

if [ ${#MISSING_SECRETS[@]} -gt 0 ]; then
  echo "❌ ERROR: Missing required secrets:"
  for SECRET in "${MISSING_SECRETS[@]}"; do
    echo "  - $SECRET"
  done
  echo ""
  echo "Create secrets with:"
  echo "  echo 'your-openai-key' | gcloud secrets create OPENAI_API_KEY --data-file=-"
  echo "  echo 'your-anthropic-key' | gcloud secrets create ANTHROPIC_API_KEY --data-file=-"
  exit 1
fi

echo "✅ All required secrets exist!"
echo ""

# ========== DEPLOY ==========
echo "🚀 Step 3/3: Deploying to Cloud Run..."

cd "$SCRIPT_DIR"
gcloud run services replace "$YAML_FILE" \
  --project="$PROJECT_ID" \
  --region="$REGION"

echo ""
echo "✅ Deployment complete!"
echo ""

# ========== POST-DEPLOY INFO ==========
echo "📊 Service Information:"
echo "----------------------------------------"

SERVICE_URL=$(gcloud run services describe "$SERVICE_NAME" \
  --project="$PROJECT_ID" \
  --region="$REGION" \
  --format="value(status.url)")

echo "Service URL: $SERVICE_URL"
echo ""

echo "Health check:"
echo "  curl $SERVICE_URL/api/health"
echo ""

echo "Chat endpoints:"
echo "  POST $SERVICE_URL/api/chat/message"
echo "  WS   $SERVICE_URL/ws/chat"
echo ""

echo "Monitoring:"
echo "  Logs:    gcloud run services logs tail $SERVICE_NAME --project=$PROJECT_ID"
echo "  Metrics: curl $SERVICE_URL/metrics"
echo ""

echo "========================================="
echo "🎉 Chat/LLM Service deployed successfully!"
echo "========================================="
