#!/bin/bash
# Deployment script for Emergence Session Service to Cloud Run
# Phase P2.3: Microservice migration - Session management service

set -e

# Configuration
PROJECT_ID="emergence-469005"
REGION="europe-west1"
SERVICE_NAME="emergence-session-service"
IMAGE_NAME="europe-west1-docker.pkg.dev/${PROJECT_ID}/app/${SERVICE_NAME}"
DOCKERFILE="infra/cloud-run/session-service.Dockerfile"

echo "💬 Deploying Emergence Session Service"
echo "========================================"
echo "Project: ${PROJECT_ID}"
echo "Region: ${REGION}"
echo "Service: ${SERVICE_NAME}"
echo ""

# Step 1: Build the Docker image
echo "📦 Step 1/3: Building Docker image..."
docker build -f ${DOCKERFILE} -t ${IMAGE_NAME}:latest .

# Tag with timestamp for versioning
TIMESTAMP=$(date +%Y%m%d%H%M%S)
docker tag ${IMAGE_NAME}:latest ${IMAGE_NAME}:${TIMESTAMP}

echo "✅ Image built: ${IMAGE_NAME}:latest"
echo "✅ Image tagged: ${IMAGE_NAME}:${TIMESTAMP}"
echo ""

# Step 2: Push to Google Artifact Registry
echo "📤 Step 2/3: Pushing image to Artifact Registry..."
docker push ${IMAGE_NAME}:latest
docker push ${IMAGE_NAME}:${TIMESTAMP}

echo "✅ Images pushed successfully"
echo ""

# Step 3: Deploy to Cloud Run
echo "🚀 Step 3/3: Deploying to Cloud Run..."
gcloud run deploy ${SERVICE_NAME} \
  --image ${IMAGE_NAME}:latest \
  --platform managed \
  --region ${REGION} \
  --project ${PROJECT_ID} \
  --allow-unauthenticated \
  --min-instances 2 \
  --max-instances 20 \
  --cpu 4 \
  --memory 2Gi \
  --timeout 900 \
  --concurrency 100 \
  --set-env-vars "SERVICE_NAME=${SERVICE_NAME},LOG_LEVEL=INFO,PORT=8080,SESSION_INACTIVITY_TIMEOUT_MINUTES=30,PROMETHEUS_ENABLED=true" \
  --service-account "486095406755-compute@developer.gserviceaccount.com"

echo ""
echo "✅ Deployment complete!"
echo ""
echo "📊 Service information:"
gcloud run services describe ${SERVICE_NAME} \
  --region ${REGION} \
  --project ${PROJECT_ID} \
  --format="value(status.url)"

echo ""
echo "🔍 Health check:"
SERVICE_URL=$(gcloud run services describe ${SERVICE_NAME} \
  --region ${REGION} \
  --project ${PROJECT_ID} \
  --format="value(status.url)")

curl -s "${SERVICE_URL}/api/health" | jq .

echo ""
echo "✨ Done! Session service is live at: ${SERVICE_URL}"
echo ""
echo "📌 Important: This service supports WebSocket connections at /ws/{session_id}"
