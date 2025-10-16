# syntax=docker/dockerfile:1
# Dockerfile for Emergence Session Service
# Manages WebSocket connections, chat sessions, and memory analysis

FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

ARG EMBED_MODEL_NAME=all-MiniLM-L6-v2
ENV EMBED_MODEL_NAME=${EMBED_MODEL_NAME}
ENV SENTENCE_TRANSFORMERS_HOME=/root/.cache/sentence_transformers
ENV HF_HOME=/root/.cache/huggingface

WORKDIR /app

# Install system dependencies for embeddings
RUN apt-get update && apt-get install -y --no-install-recommends \
      build-essential \
    && rm -rf /var/lib/apt/lists/*

# Create minimal requirements file for session service
COPY infra/cloud-run/session-requirements.txt requirements.txt
RUN python -m pip install --upgrade pip && pip install -r requirements.txt

# Pre-download the embedding model
RUN python -c "import os; from sentence_transformers import SentenceTransformer; model_name = os.environ.get('EMBED_MODEL_NAME', 'all-MiniLM-L6-v2'); SentenceTransformer(model_name)"

# Copy only the necessary source files
COPY src/backend/__init__.py src/backend/
COPY src/backend/main.py src/backend/
COPY src/backend/containers.py src/backend/
COPY src/backend/core/ src/backend/core/
COPY src/backend/features/chat/ src/backend/features/chat/
COPY src/backend/features/memory/ src/backend/features/memory/
COPY src/backend/features/threads/ src/backend/features/threads/
COPY src/backend/shared/ src/backend/shared/

# Create necessary directories
RUN mkdir -p /app/data /app/.chroma

# Cloud Run exposes $PORT
ENV PORT=8080
ENV SERVICE_MODE=session

# Run with WebSocket support
CMD ["sh", "-c", "python -m uvicorn --app-dir src backend.main:app --host 0.0.0.0 --port ${PORT:-8080} --ws websockets"]
