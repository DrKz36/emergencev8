# syntax=docker/dockerfile:1.7

# --- Base Python slim ---
FROM python:3.11-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    # Ports/paths par défaut compatibles Cloud Run
    PORT=8080 \
    EMERGENCE_DB_PATH=/tmp/emergence.db \
    EMERGENCE_VECTOR_DIR=/tmp/chroma \
    EMERGENCE_UPLOADS_DIR=/tmp/uploads \
    # Caches HF/Transformers -> /tmp (R/W en Cloud Run)
    HF_HOME=/tmp/hf \
    TRANSFORMERS_CACHE=/tmp/hf \
    HUGGINGFACE_HUB_CACHE=/tmp/hf \
    SENTENCE_TRANSFORMERS_HOME=/tmp/hf

# Déps système minimalistes (certifs, build libs légères si besoin)
RUN apt-get update -y && apt-get install -y --no-install-recommends \
      build-essential curl ca-certificates git \
    && rm -rf /var/lib/apt/lists/*

# --- Dossier app ---
WORKDIR /app

# Copie requirements d'abord pour optimiser le cache
COPY requirements.txt /app/requirements.txt

# Install deps (wheel accélère)
RUN python -m pip install --upgrade pip wheel && \
    python -m pip install -r /app/requirements.txt

# Copie code (backend+frontend assets utiles au backend si nécessaire)
COPY . /app

# Expose non strictement nécessaire pour Cloud Run, mais explicite :
EXPOSE 8080

# S’assure que les répertoires R/W existent au démarrage
# et démarre uvicorn en écoutant **le PORT fourni par Cloud Run**
# (Cloud Run injecte PORT au runtime; fallback déjà à 8080 via ENV)
CMD ["sh","-c", "\
  mkdir -p ${EMERGENCE_VECTOR_DIR} ${EMERGENCE_UPLOADS_DIR} ${HF_HOME} && \
  python -m uvicorn --app-dir src backend.main:app --host 0.0.0.0 --port ${PORT} \
"]
