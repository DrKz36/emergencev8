# =========================
#   ÉMERGENCE – Dockerfile
#   Hotfix static v7.4
# =========================

# ---- Base ----
FROM python:3.11-slim AS base

# Hygiene Python
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# Paquets système minimaux
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential curl && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# ---- Dépendances Python (cache efficace) ----
COPY requirements.txt ./requirements.txt
RUN python -m pip install --upgrade pip && \
    pip install -r requirements.txt

# ---- Cache-bust pour s'assurer que les modifications code/statics prennent ----
ARG BUILDSTAMP
ENV BUILDSTAMP=${BUILDSTAMP}

# ---- Statiques + Code (ordre de COPY calibré) ----
# 1) Fichiers front à la racine (servis par main.py)
COPY index.html ./index.html
# 2) Assets (si présent dans le repo). Ne casse pas si absent (COPY échouera si inexistant, donc laisse le dossier au repo).
#    Si tu n'as pas de dossier assets, commente la ligne suivante.
COPY assets ./assets
# 3) Code applicatif complet (backend + frontend)
COPY src ./src

# ---- Env runtime utiles ----
ENV CHROMA_DISABLE_TELEMETRY=1 \
    HF_HOME=/app/.cache/hf \
    VECTOR_STORE_DIR=/app/data/vector_store

RUN mkdir -p /app/data/vector_store

# ---- Exposition Cloud Run ----
EXPOSE 8080

# ---- Commande (alignée Cloud Run) ----
# Uvicorn doit écouter 0.0.0.0:8080
CMD ["uvicorn", "--app-dir", "src", "backend.main:app", "--host", "0.0.0.0", "--port", "8080"]
