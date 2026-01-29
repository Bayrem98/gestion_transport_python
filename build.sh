#!/usr/bin/env bash
# build.sh

echo "🚀 Début de l'installation..."

# Mettre à jour pip
pip install --upgrade pip

# Installer les dépendances
pip install -r requirements.txt

# Collecter les fichiers statiques
python manage.py collectstatic --noinput

# Appliquer les migrations
python manage.py migrate

echo "✅ Installation terminée !"