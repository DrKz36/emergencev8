# syntax=docker/dockerfile:1

FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

ARG EMBED_MODEL_NAME=all-MiniLM-L6-v2
ENV EMBED_MODEL_NAME=${EMBED_MODEL_NAME}
ENV SENTENCE_TRANSFORMERS_HOME=/root/.cache/sentence_transformers \
    HF_HOME=/root/.cache/huggingface

# System dependencies (build essentials + libmagic + node.js for frontend build)
RUN apt-get update && apt-get install -y --no-install-recommends \
      build-essential libmagic1 curl \
    && curl -fsSL https://deb.nodesource.com/setup_18.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Python dependencies
COPY requirements.txt .
RUN python -m pip install --upgrade pip && pip install -r requirements.txt

# Pre-download the embedding model (requires online access)
RUN python -c "import os; from sentence_transformers import SentenceTransformer; model_name = os.environ.get('EMBED_MODEL_NAME', 'all-MiniLM-L6-v2'); SentenceTransformer(model_name)"

# Now set offline mode to prevent runtime downloads
ENV HF_HUB_OFFLINE=1 \
    TRANSFORMERS_OFFLINE=1

# Frontend dependencies and build
COPY package.json package-lock.json ./
RUN npm ci --only=production

# Copy application code
COPY . .

# Build frontend (generates dist/ with updated version.js)
RUN npm run build

# Copy built frontend files to root for FastAPI to serve
RUN cp -r dist/* . && rm -rf dist

# Cloud Run exposes $PORT
ENV PORT=8080
CMD ["sh", "-c", "python -m uvicorn --app-dir src backend.main:app --host 0.0.0.0 --port ${PORT:-8080}"]
