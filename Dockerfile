# =========================
#   ÉMERGENCE – Dockerfile
#   Hotfix static v7.4.1
# =========================

FROM python:3.11-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential curl && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# -- Dépendances Python (cache) --
COPY requirements.txt ./requirements.txt
RUN python -m pip install --upgrade pip && pip install -r requirements.txt

# -- Cache-bust dur (change à chaque build) --
ARG BUILDSTAMP
ENV BUILDSTAMP=${BUILDSTAMP}

# -- Statiques + Code (ordre important) --
COPY index.html ./index.html
# Si tu n'as pas de dossier assets, commente la ligne suivante.
COPY assets ./assets
COPY src ./src

# -- Envs runtime --
ENV CHROMA_DISABLE_TELEMETRY=1 \
    HF_HOME=/app/.cache/hf \
    VECTOR_STORE_DIR=/app/data/vector_store
RUN mkdir -p /app/data/vector_store

EXPOSE 8080

CMD ["uvicorn", "--app-dir", "src", "backend.main:app", "--host", "0.0.0.0", "--port", "8080"]
