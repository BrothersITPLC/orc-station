#!/bin/sh
echo "Starting cron daemon..."
cron

echo "Starting Django runserver..."
exec python manage.py runserver 0.0.0.0:8000