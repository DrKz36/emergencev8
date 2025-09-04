# Dockerfile — ÉMERGENCE (Cloud Run ready, sans overrides)
FROM python:3.11-slim

# --- Runtime/env de base
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

# Cloud Run écoute sur 8080 ; on fixe le port côté uvicorn (pas de shell-expansion)
ENV PORT=8080

# Optionnel : facilite les imports "backend.*" depuis /app/src
ENV PYTHONPATH=/app/src

# --- OS deps minimales
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential curl ca-certificates \
 && rm -rf /var/lib/apt/lists/*

# --- Répertoire de travail
WORKDIR /app

# --- Dépendances (caching)
COPY requirements.txt /app/requirements.txt
RUN python -m pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# --- Code
COPY . /app

# --- Réseau
EXPOSE 8080

# --- Exécution
# IMPORTANT : pas de shell, pas de concaténation d’args.
# On utilise la forme exec JSON pour éviter tout collage d'arguments.
# PYTHONPATH pointe déjà sur /app/src, mais on garde --app-dir=src pour expliciter.
CMD ["python", "-m", "uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8080", "--app-dir", "src"]
