import os
from datetime import timedelta
from pathlib import Path

from celery.schedules import crontab
from decouple import config
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY")

DEBUG = os.environ.get("DJANGO_DEBUG") != "False"

ROOT_URLCONF = "InsaBackednLatest.urls"
LANGUAGE_CODE = "en-us"
USE_I18N = True
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True
ALLOWED_HOSTS = os.environ.get("DJANGO_ALLOWED_HOSTS", "").split(",")
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [os.path.join(BASE_DIR, "templates")],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]


# Custom user model
AUTH_USER_MODEL = "users.CustomUser"
AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
]

# Database
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get("POSTGRES_DB"),
        "USER": os.environ.get("POSTGRES_USER"),
        "PASSWORD": os.environ.get("POSTGRES_PASSWORD"),
        "HOST": os.environ.get("POSTGRES_HOST"),
        "PORT": os.environ.get("POSTGRES_PORT"),
        "CONN_MAX_AGE": 60, 
        "CONN_HEALTH_CHECKS": True, 
        "OPTIONS": {
            "connect_timeout": 10,  
            "options": "-c statement_timeout=30000"  
        },
    },
    "central": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get("POSTGRES_DB"),
        "USER": os.environ.get("POSTGRES_USER"),
        "PASSWORD": os.environ.get("POSTGRES_PASSWORD"),
        "HOST": "local_postgres",
        "PORT": 5432,
        "CONN_MAX_AGE": 60,
        "CONN_HEALTH_CHECKS": True,
        "OPTIONS": {
            "connect_timeout": 10,
            "options": "-c statement_timeout=30000"
        },
    },
}


# Email settings
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = "smtp.gmail.com"
EMAIL_PORT = os.environ.get("EMAIL_PORT")
EMAIL_USE_TLS = os.environ.get("EMAIL_USE_TLS", "True") == "True"
EMAIL_HOST_USER = os.environ.get("EMAIL_HOST_USER")
EMAIL_HOST_PASSWORD = os.environ.get("EMAIL_HOST_PASSWORD")
WSGI_APPLICATION = "InsaBackednLatest.wsgi.application"
CORS_ALLOW_CREDENTIALS = os.environ.get("CORS_ALLOW_CREDENTIALS") == "True"
CORS_ALLOW_HEADERS = os.environ.get("CORS_ALLOW_HEADERS", "").split(",")
ALLOWED_HOSTS.append("*")
CORS_ALLOW_METHODS = os.environ.get("CORS_ALLOW_METHODS", "").split(",")

CORS_ALLOW_METHODS.extend(["OPTIONS", "GET", "POST", "PUT", "DELETE"])
# JWT settings
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(
        minutes=int(os.environ.get("JWT_ACCESS_TOKEN_LIFETIME", "15"))
    ),
    "REFRESH_TOKEN_LIFETIME": timedelta(
        days=int(os.environ.get("JWT_REFRESH_TOKEN_LIFETIME", "1"))
    ),
    "SIGNING_KEY": SECRET_KEY,
    "VERIFYING_KEY": os.environ.get("JWT_VERIFYING_KEY", SECRET_KEY),
    "AUTH_HEADER_TYPES": ("Bearer",),
}

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "rest_framework_api_key",
    "rest_framework.authtoken",
    "django_filters",
    "corsheaders",
    "auditlog",
    "django_crontab",
    # Moved to correct position
    "users",
    "address",
    "drivers",
    "workstations",
    "trucks",
    "declaracions",
    "exporters",
    "tax",
    "analysis",
    "drf_yasg",
    "django_pandas",
    "core",
    "localcheckings",
    "audit",
    "path",
    "news",
    "api",
    "orcSync",
    "django_celery_beat",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "common.middleware.DisableCSRFForAPIMiddleware",  
    # "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "common.middleware.AttachJWTTokenMiddleware",
    "common.middleware.RefreshTokenMiddleware",
    "common.middleware.DisplayCurrentUserMiddleware",
]
# External APIs and Tokens
DERASH_API_KEY = os.environ.get("DERASH_API_KEY")
DERASH_SECRET_KEY = os.environ.get("DERASH_SECRET_KEY")
DERASH_END_POINT = os.environ.get("DERASH_END_POINT")
WEIGHTBRIDGE_TOKEN = os.environ.get("WEIGHTBRIDGE_TOKEN")
EXTERNAL_URI_WEIGHT_BRIDGE = os.environ.get("EXTERNAL_URI_WEIGHT_BRIDGE")
QR_ENCRYPTION_KEY = "eyJuYW1lIjoiT3JvbWlhIFJldmVudWUiLCJ"
STATIC_URL = "/static/"
# CORS and CSRF settings
CORS_ALLOWED_ORIGINS = os.environ.get("CORS_ALLOWED_ORIGINS", "").split(",")
CSRF_TRUSTED_ORIGINS = os.environ.get("CSRF_TRUSTED_ORIGINS", "").split(",")

# Media settings
MEDIA_ROOT = os.environ.get("MEDIA_ROOT", "/app/media")
MEDIA_URL = os.environ.get("MEDIA_URL", "/media/")

STATIC_ROOT = BASE_DIR / "staticfiles"

STATICFILES_DIRS = [
    BASE_DIR / "static",
]


DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

CELERY_BROKER_URL = config("CELERY_BROKER_URL", default="redis://redis:6379/0")
CELERY_RESULT_BACKEND = config("CELERY_RESULT_BACKEND", default="redis://redis:6379/1")


CELERY_TASK_ACKS_LATE = True
CELERY_TASK_REJECT_ON_WORKER_LOST = True
CELERY_WORKER_PREFETCH_MULTIPLIER = 1  
CELERY_WORKER_MAX_TASKS_PER_CHILD = 50  

CELERY_TASK_SOFT_TIME_LIMIT = 300 
CELERY_TASK_TIME_LIMIT = 360       

CELERY_TASK_RETRY_POLICY = {
    "max_retries": 3,
    "interval_start": 5,
    "interval_step": 10,
    "interval_max": 60,
}

CELERY_BEAT_SCHEDULE = {
    "sync-with-central": {
        "task": "orcSync.tasks.main_sync.run_sync_task",
        "schedule": crontab(minute=f"*/{os.environ.get('CELERY_SCHEDULE')}"),
        "options": {
            "expires": 240, 
        },
    },
}

SYNCHRONIZABLE_MODELS = [
    "drivers.Driver",
    "workstations.WorkStation",
    "workstations.WorkedAt",
    "trucks.TruckOwner",
    "trucks.Truck",
    "exporters.TaxPayerType",
    "exporters.Exporter",
    "tax.Tax",
    "users.Report",
    "users.UserStatus",
    "users.CustomUser",
    "users.Department",
    "address.RegionOrCity",
    "address.ZoneOrSubcity",
    "address.Woreda",
    "declaracions.Commodity",
    "declaracions.PaymentMethod",
    "declaracions.Declaracion",
    "declaracions.Checkin",
    "declaracions.ChangeTruck",
    "declaracions.ManualPayment",
    "auth.Group",
    "path.Path",
    "path.PathStation",
]

USE_X_FORWARDED_HOST = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
