# syntax=docker/dockerfile:1
FROM python:3.11-slim

# --- Base env ---
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=on \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    PIP_DEFAULT_TIMEOUT=100 \
    # Vector store/transformers caches si besoin
    HF_HOME=/app/.cache/hf \
    # Cloud Run fournit PORT, on garde un défaut local
    PORT=8080 \
    # Pour imports "backend.*" sans --app-dir (belt & suspenders)
    PYTHONPATH=/app/src

# --- OS deps ---
# curl pour HEALTHCHECK ; tini pour reap PID1 ; build-essential pour roues natives courantes
RUN apt-get update && apt-get install -y --no-install-recommends \
      build-essential curl ca-certificates git tini \
    && rm -rf /var/lib/apt/lists/*

# --- Workdir ---
WORKDIR /app

# --- Python deps ---
# Astuce: couche stable requirements pour cacher au max
COPY requirements.txt /app/requirements.txt
RUN python -m pip install --upgrade pip \
 && python -m pip install -r /app/requirements.txt

# --- Code ---
# On copie explicitement src/ ; .dockerignore DOIT exclure .git, .venv, node_modules, etc.
COPY src/ /app/src/
# (facultatif) si tu as des assets publics à servir (sinon commente)
# COPY public/ /app/public/

# --- Sécurité runtime (non-root) ---
# On crée un user "app" et on s’assure que /app est writable (ex: /app/data pour Chroma etc.)
RUN useradd -r -u 10001 -g root app \
 && mkdir -p /app/data /app/.cache \
 && chown -R app:root /app
USER app

# --- Réseau & health ---
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
  CMD curl -fsS http://127.0.0.1:${PORT}/api/health || exit 1

# --- Entry & CMD ---
# tini comme PID1 pour un shutdown propre
ENTRYPOINT ["tini","--"]

# ⚠️ LANCE LE WRAPPER SÉCURISÉ (bloque .git/.env etc.)
# On passe par sh -c pour l’expansion ${PORT} de Cloud Run
CMD ["sh","-c","uvicorn --app-dir src backend.asgi_secure:app --host 0.0.0.0 --port ${PORT}"]
