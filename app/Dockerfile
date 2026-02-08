# ===========================================
# WoW Mythic Raid Scraper
# ===========================================
FROM python:3.11-slim

LABEL maintainer="EPSI DataMart Team"
LABEL description="WarcraftLogs API Scraper for Mythic Raid Analytics"

# Variables d'environnement
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Repertoire de travail
WORKDIR /app

# Copie des fichiers de dependances
COPY requirements.txt .

# Installation des dependances Python (PyMySQL est un driver pur Python, pas besoin de libs C)
RUN pip install --no-cache-dir -r requirements.txt

# Copie du code source
COPY . .

# Creation du repertoire de logs
RUN mkdir -p /app/logs

# Commande par defaut
CMD ["python", "run_all.py"]
