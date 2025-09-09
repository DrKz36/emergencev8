# syntax=docker/dockerfile:1
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    PIP_NO_CACHE_DIR=off \
    EMERGENCE_FAST_BOOT= \
    EMERGENCE_SKIP_MIGRATIONS=

WORKDIR /app

# Déps système minimales
RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates curl \
 && rm -rf /var/lib/apt/lists/*

# Déps Python
COPY requirements.txt ./requirements.txt
RUN python -m pip install --upgrade pip && pip install -r requirements.txt

# Code + entrypoint
COPY . /app
COPY entrypoint.py /app/entrypoint.py

EXPOSE 8080
CMD ["python", "/app/entrypoint.py"]
