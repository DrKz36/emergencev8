# syntax=docker/dockerfile:1

FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# Dépendances système minimales (build + libmagic pour python-magic)
RUN apt-get update && apt-get install -y --no-install-recommends \
      build-essential libmagic1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Dépendances Python
COPY requirements.txt .
RUN python -m pip install --upgrade pip && pip install -r requirements.txt

# Code
COPY . .

# Cloud Run expose $PORT
ENV PORT=8080
CMD ["sh", "-c", "python -m uvicorn --app-dir src backend.main:app --host 0.0.0.0 --port ${PORT:-8080}"]
