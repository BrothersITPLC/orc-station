#!/bin/sh
set -e

echo "Waiting for database to be ready..."
until python manage.py migrate --check > /dev/null 2>&1; do
  echo "Database not ready or migrations not applied, retrying in 5s..."
  sleep 5
done

echo "Starting Celery Beat..."
celery -A InsaBackednLatest beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler
