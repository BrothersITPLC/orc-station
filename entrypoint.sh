#!/bin/bash
set -e

echo "🚀 Waiting for database..."
until pg_isready -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USER" > /dev/null 2>&1; do
  echo "Database not ready, retrying in 3s..."
  sleep 3
done
echo "✅ Database ready"

echo "🧩 Applying migrations..."
python manage.py makemigrations --noinput || true
python manage.py migrate --noinput || true

echo "📦 Collecting static files..."
python manage.py collectstatic --noinput || true

echo "🎯 Starting Gunicorn server..."
exec gunicorn InsaBackednLatest.wsgi:application --bind 0.0.0.0:8000
