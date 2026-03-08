# Dockerfile pour FrigoScan (FastAPI)
FROM python:3.10-slim

# Variables d'environnement
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Dépendances système minimales
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Création du dossier de l'app
WORKDIR /app

# Copie des fichiers de dépendances
COPY requirements.txt ./

# Installation des dépendances Python
RUN pip install --no-cache-dir -r requirements.txt

# Copie du code de l'application
COPY . .

# Exposition du port
EXPOSE 8000

# Commande de lancement (production, pas de reload)
CMD ["uvicorn", "server.main:app", "--host", "0.0.0.0", "--port", "8000"]
