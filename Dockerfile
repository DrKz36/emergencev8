# syntax=docker/dockerfile:1.7-labs

############################
# Stage 1 — Frontend deps  #
############################
FROM node:20-alpine AS frontend-deps
WORKDIR /front

# Déps front (cache npm)
COPY package.json package-lock.json* pnpm-lock.yaml* yarn.lock* ./
RUN --mount=type=cache,target=/root/.npm npm ci

############################
# Stage 2 — Frontend build #
############################
FROM frontend-deps AS frontend-build
WORKDIR /front

# Sources front
COPY vite.config.js ./vite.config.js
COPY index.html ./index.html
COPY assets ./assets
COPY src/frontend ./src/frontend
# Shim exigé car index.html référence /src/main.js
COPY src/main.js ./src/main.js

# Build Vite -> dist/
RUN npm run build

############################
# Stage 3 — Py deps (venv) #
############################
FROM python:3.11-slim AS pydeps
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 \
    VIRTUAL_ENV=/opt/venv
ENV PATH="$VIRTUAL_ENV/bin:$PATH"
WORKDIR /app

RUN python -m venv "$VIRTUAL_ENV"
COPY requirements.txt ./requirements.txt
# Déps Python (cache pip)
RUN --mount=type=cache,target=/root/.cache/pip pip install --no-cache-dir -r requirements.txt

############################
# Stage 4 — Runtime        #
############################
FROM python:3.11-slim AS runtime
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 \
    VIRTUAL_ENV=/opt/venv
ENV PATH="$VIRTUAL_ENV/bin:$PATH"
WORKDIR /app

# Outils légers (si besoin d’un wheel natif)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl ca-certificates && rm -rf /var/lib/apt/lists/*

# Déps Python prêtes
COPY --from=pydeps $VIRTUAL_ENV $VIRTUAL_ENV

# Code backend + ressources
COPY src ./src
COPY assets ./assets
COPY index.html ./index.html

# Bundle front prêt à servir par le backend
COPY --from=frontend-build /front/dist/ /app/static/

# Répertoire DB/cache (évite FileNotFoundError au boot)
RUN mkdir -p /app/data

EXPOSE 8080
# Cloud Run fournit $PORT → écoute dynamique
CMD ["sh","-c","uvicorn --app-dir src backend.main:app --host 0.0.0.0 --port ${PORT:-8080}"]
