# ---------- 1) FRONTEND BUILD (Vite) ----------
FROM node:20-alpine AS frontend
WORKDIR /app

# Install deps (verrouillé par package-lock)
COPY package.json package-lock.json ./
RUN npm ci --no-audit --no-fund

# Copie du code (index.html + src/** + assets/** + vite.config.js)
COPY . .

# Build production -> dist/
RUN npm run build

# ---------- 2) BACKEND RUNTIME ----------
FROM python:3.11-slim AS runtime
WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    STATIC_DIR=/app/static

# Dépendances Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Backend
COPY src ./src
COPY entrypoint.sh .

# Front build + assets statiques
COPY --from=frontend /app/dist   ./static
COPY --from=frontend /app/assets ./assets

# Port Cloud Run
EXPOSE 8080

# Uvicorn (CMD figée)
CMD ["uvicorn", "--app-dir", "src", "backend.main:app", "--host", "0.0.0.0", "--port", "8080"]
