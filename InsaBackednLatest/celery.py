# InsaBackednLatest/celery.py
import os

from celery import Celery

# set the Django settings module for the 'celery' program
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InsaBackednLatest.settings")

# create the celery app
app = Celery("InsaBackednLatest")

# read configuration from Django settings, CELERY namespace means CELERY_*
app.config_from_object("django.conf:settings", namespace="CELERY")

# automatically discover tasks.py in all installed apps
app.autodiscover_tasks()
