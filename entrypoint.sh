#!/bin/sh

# Applica le migrazioni del database Django
echo "Applying database migrations..."
python manage.py migrate --no-input

# Avvia il server Gunicorn
echo "Starting Gunicorn server..."
gunicorn core.wsgi:application --bind 0.0.0.0:8000 --workers 4