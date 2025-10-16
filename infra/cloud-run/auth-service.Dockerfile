# syntax=docker/dockerfile:1
# Dockerfile for Emergence Authentication Service
# Lightweight FastAPI service for authentication, sessions, and user management

FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Install minimal system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
      build-essential \
    && rm -rf /var/lib/apt/lists/*

# Create minimal requirements file for auth service
# Only include what's needed for FastAPI + Auth
COPY infra/cloud-run/auth-requirements.txt requirements.txt
RUN python -m pip install --upgrade pip && pip install -r requirements.txt

# Copy only the necessary source files
COPY src/backend/__init__.py src/backend/
COPY src/backend/main.py src/backend/
COPY src/backend/containers.py src/backend/
COPY src/backend/core/ src/backend/core/
COPY src/backend/features/auth/ src/backend/features/auth/
COPY src/backend/shared/ src/backend/shared/

# Create data directory for SQLite
RUN mkdir -p /app/data

# Cloud Run exposes $PORT
ENV PORT=8080
ENV SERVICE_MODE=auth

# Run only the auth-related endpoints
CMD ["sh", "-c", "python -m uvicorn --app-dir src backend.main:app --host 0.0.0.0 --port ${PORT:-8080}"]
