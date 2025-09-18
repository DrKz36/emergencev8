# syntax=docker/dockerfile:1

FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

ARG EMBED_MODEL_NAME=all-MiniLM-L6-v2
ENV EMBED_MODEL_NAME=${EMBED_MODEL_NAME}
ENV SENTENCE_TRANSFORMERS_HOME=/root/.cache/sentence_transformers
ENV HF_HOME=/root/.cache/huggingface

# System dependencies (build essentials + libmagic for python-magic)
RUN apt-get update && apt-get install -y --no-install-recommends \
      build-essential libmagic1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Python dependencies
COPY requirements.txt .
RUN python -m pip install --upgrade pip && pip install -r requirements.txt

# Pre-download the embedding model so Cloud Run stays offline-friendly
RUN python -c "import os; from sentence_transformers import SentenceTransformer; model_name = os.environ.get('EMBED_MODEL_NAME', 'all-MiniLM-L6-v2'); SentenceTransformer(model_name)"

# Application code
COPY . .

# Cloud Run exposes $PORT
ENV PORT=8080
CMD ["sh", "-c", "python -m uvicorn --app-dir src backend.main:app --host 0.0.0.0 --port ${PORT:-8080}"]
