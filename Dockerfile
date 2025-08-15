# Utiliser Python officiel
FROM python:3.11-slim

# Variables d'environnement
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PORT=8080

# Installer les dépendances système minimales
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Définir le dossier de travail
WORKDIR /app

# Copier le requirements.txt et installer les dépendances
COPY requirements.txt ./
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Copier tout le code du projet
COPY . .

# Exposer le port Cloud Run
EXPOSE 8080

# Commande de démarrage
CMD ["python", "-m", "uvicorn", "--app-dir", "src", "backend.main:app", "--host", "0.0.0.0", "--port", "8080"]
