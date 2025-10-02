# #orcSync/models/orc_sync.py
# ```
# import uuid

# from django.contrib.contenttypes.fields import GenericForeignKey
# from django.contrib.contenttypes.models import ContentType
# from django.core.exceptions import ValidationError
# from django.db import models

# from base.models import BaseModel
# from workstations.models import WorkStation


# class CentralServerCredential(BaseModel):
#     """
#     A singleton model to store this workstation's own identity and the
#     connection details for the one central server it syncs with.

#     Only one instance of this model should ever exist.
#     """

#     location = models.OneToOneField(
#         WorkStation, related_name="sync_credential", on_delete=models.CASCADE
#     )
#     base_url = models.CharField(
#         max_length=255,
#         help_text="The base URL of the central server's API. E.g., https://api.mycompany.com",
#     )
#     api_key = models.CharField(
#         max_length=255, help_text="The secret API key assigned to this workstation."
#     )

#     def __str__(self):
#         return f"Credentials for Central Server ({self.base_url})"

#     def save(self, *args, **kwargs):
#         """
#         Overrides the save method to ensure only one instance can be created.
#         """
#         if not self.pk and CentralServerCredential.objects.exists():
#             raise ValidationError(
#                 "Only one CentralServerCredential instance can be created."
#             )
#         return super().save(*args, **kwargs)


# class LocalChangeLog(BaseModel):
#     """
#     Logs all local Create, Update, and Delete operations that need to be
#     pushed to the central server. This acts as a resilient "outbox".
#     """

#     class Action(models.TextChoices):
#         CREATED = "C", "Created"
#         UPDATED = "U", "Updated"
#         DELETED = "D", "Deleted"

#     class Status(models.TextChoices):
#         PENDING = "P", "Pending"
#         SENT = "S", "Sent"
#         FAILED = "F", "Failed"
#         ACKNOWLEDGED = (
#             "A",
#             "Acknowledged",
#         )

#     id = models.BigAutoField(primary_key=True)
#     event_uuid = models.UUIDField(
#         default=uuid.uuid4,
#         editable=False,
#         unique=True,
#         help_text="Unique ID for this event, sent to the server for acknowledgement.",
#     )

#     content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
#     object_id = models.CharField(max_length=255)
#     changed_object = GenericForeignKey("content_type", "object_id")
#     retry_count = models.PositiveIntegerField(
#         default=0, help_text="Number of times this entry has failed to sync."
#     )
#     action = models.CharField(max_length=1, choices=Action.choices)
#     data_payload = models.JSONField(
#         help_text="A JSON snapshot of the model's data to be sent."
#     )

#     status = models.CharField(
#         max_length=1, choices=Status.choices, default=Status.PENDING, db_index=True
#     )

#     timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
#     sent_at = models.DateTimeField(
#         null=True, blank=True, help_text="Timestamp of the last push attempt."
#     )
#     error_message = models.TextField(
#         blank=True, null=True, help_text="Stores the error response if a push fails."
#     )

#     class Meta:
#         ordering = ["timestamp"]

#     def __str__(self):
#         return f"[{self.get_status_display()}] {self.get_action_display()} on {self.content_type.model} @ {self.timestamp}"

# ```

# #orcSync/functions/client.py
# ```
# import requests
# from django.core.exceptions import ImproperlyConfigured

# from orcSync.models import CentralServerCredential


# class CentralAPIClient:
#     """
#     A client for communicating with the central server's sync API.
#     Handles authentication and constructs requests.
#     """

#     _credentials = None

#     def _get_credentials(self):
#         """
#         Fetches and caches the central server credentials.
#         Raises an error if credentials are not configured.
#         """
#         if self._credentials is None:
#             try:
#                 self._credentials = CentralServerCredential.objects.first()
#                 if self._credentials is None:
#                     raise CentralServerCredential.DoesNotExist
#             except CentralServerCredential.DoesNotExist:
#                 raise ImproperlyConfigured(
#                     "Central Server Credentials are not configured. "
#                     "Please create a CentralServerCredential entry in the admin."
#                 )
#         return self._credentials

#     def _get_headers(self):
#         """Constructs the authorization headers."""
#         creds = self._get_credentials()
#         print(f"the centeral api-key{creds.api_key}")
#         return {
#             "Authorization": f"Api-Key {creds.api_key}",
#             "Content-Type": "application/json",
#         }

#     def _get_url(self, endpoint):
#         """Constructs the full URL for a given API endpoint."""
#         creds = self._get_credentials()
#         return f"{creds.base_url.rstrip('/')}/api/sync/{endpoint.lstrip('/')}"

#     def get_pending_changes(self):
#         """
#         Fetches all pending changes for this workstation from the central server.
#         """
#         url = self._get_url("get-pending/")
#         try:
#             response = requests.get(url, headers=self._get_headers(), timeout=30)
#             response.raise_for_status()
#             return response.json()
#         except requests.RequestException as e:
#             print(f"Error fetching pending changes: {e}")
#             return None

#     def push_changes(self, changes_payload):
#         """
#         Pushes a list of local changes to the central server.
#         """
#         if not changes_payload:
#             return True, "No changes to push."

#         url = self._get_url("push/")
#         try:
#             response = requests.post(
#                 url, headers=self._get_headers(), json=changes_payload, timeout=60
#             )
#             response.raise_for_status()
#             return True, response.json()
#         except requests.RequestException as e:
#             print(f"Error pushing changes: {e}")
#             return False, str(e)

#     def acknowledge_changes(self, event_ids):
#         """
#         Acknowledges receipt and successful processing of a list of change event IDs.
#         """
#         if not event_ids:
#             return True, "No events to acknowledge."

#         url = self._get_url("acknowledge/")
#         payload = {"acknowledged_events": event_ids}
#         try:
#             response = requests.post(
#                 url, headers=self._get_headers(), json=payload, timeout=30
#             )
#             response.raise_for_status()
#             return True, response.json()
#         except requests.RequestException as e:
#             print(f"Error acknowledging changes: {e}")
#             return False, str(e)

# ```

# #orcSync/functions/orchestrator.py
# ```
# import base64

# import requests
# from django.apps import apps
# from django.core.files.base import ContentFile
# from django.db import models, transaction
# from django.db.models import F, Q
# from django.db.models.signals import post_save, pre_delete

# from orcSync.models import LocalChangeLog

# from .client import CentralAPIClient

# MAX_RETRIES = 5


# def _apply_server_changes(changes, api_client):
#     """
#     Processes and applies changes received from the server.
#     Handles creation, updates, and deletion of local objects, including file downloads.
#     NEW: Acknowledges successful changes in small batches for resilience.
#     """
#     applied_event_ids_batch = []
#     batch_size = 10

#     from orcSync.signals import handle_delete, handle_save

#     for i, change in enumerate(changes):
#         model_label = change["model"]
#         object_id = change["object_id"]
#         action = change["action"]
#         payload = change["data_payload"]

#         try:
#             Model = apps.get_model(model_label)

#             post_save.disconnect(
#                 handle_save, sender=Model, dispatch_uid=f"sync_save_{Model._meta.label}"
#             )
#             pre_delete.disconnect(
#                 handle_delete,
#                 sender=Model,
#                 dispatch_uid=f"sync_delete_{Model._meta.label}",
#             )

#             with transaction.atomic():
#                 if action == "C" or action == "U":
#                     file_urls, data_fields = {}, {}
#                     for field_name, value in payload.items():
#                         if not hasattr(Model, field_name):
#                             continue
#                         field_obj = Model._meta.get_field(field_name)
#                         if (
#                             isinstance(field_obj, models.FileField)
#                             and isinstance(value, str)
#                             and value.startswith("http")
#                         ):
#                             file_urls[field_name] = value
#                         else:
#                             data_fields[field_name] = value

#                     instance, created = Model.objects.update_or_create(
#                         pk=object_id, defaults=data_fields
#                     )

#                     for field_name, url in file_urls.items():
#                         try:
#                             response = requests.get(url, stream=True)
#                             response.raise_for_status()
#                             filename = url.split("/")[-1]
#                             getattr(instance, field_name).save(
#                                 filename, ContentFile(response.content), save=True
#                             )
#                         except requests.RequestException as e:
#                             print(
#                                 f"SYNC ERROR: Failed to download file for {object_id} from {url}. Error: {e}"
#                             )

#                 elif action == "D":
#                     instance_to_delete = Model.objects.filter(pk=object_id).first()
#                     if instance_to_delete:
#                         instance_to_delete._is_sync_operation = True
#                         instance_to_delete.delete()

#             applied_event_ids_batch.append(change["id"])

#         except LookupError:
#             print(
#                 f"SYNC WARNING: Model {model_label} not found locally. Skipping change."
#             )
#         except Exception as e:
#             print(f"SYNC ERROR: Failed applying change {change['id']}: {e}. Skipping.")
#         finally:
#             post_save.connect(
#                 handle_save, sender=Model, dispatch_uid=f"sync_save_{Model._meta.label}"
#             )
#             pre_delete.connect(
#                 handle_delete,
#                 sender=Model,
#                 dispatch_uid=f"sync_delete_{Model._meta.label}",
#             )

#         is_batch_full = len(applied_event_ids_batch) >= batch_size
#         is_last_item = (i + 1) == len(changes)

#         if (is_batch_full or is_last_item) and applied_event_ids_batch:
#             print(
#                 f"Acknowledging batch of {len(applied_event_ids_batch)} applied changes..."
#             )
#             success, _ = api_client.acknowledge_changes(applied_event_ids_batch)
#             if not success:
#                 print(
#                     "SYNC WARNING: Failed to acknowledge batch. These changes may be re-downloaded later."
#                 )

#             applied_event_ids_batch = []


# def run_sync_cycle():
#     """
#     Executes the full "receive-first, send-second" synchronization cycle.
#     This is the main function to call to trigger a sync.
#     """
#     print("Starting sync cycle...")
#     api_client = CentralAPIClient()

#     print("Phase 1: Receiving changes from central server...")
#     server_data = api_client.get_pending_changes()

#     if server_data is None:
#         print("Sync cycle failed: Could not connect to central server.")
#         return

#     pending_changes = server_data.get("pending_changes", [])
#     if pending_changes:
#         print(f"Applying {len(pending_changes)} server changes...")
#         _apply_server_changes(pending_changes, api_client)
#     else:
#         print("No pending changes to apply from server.")

#     acknowledged_events = server_data.get("acknowledged_events", [])
#     if acknowledged_events:
#         LocalChangeLog.objects.filter(
#             event_uuid__in=acknowledged_events, status=LocalChangeLog.Status.SENT
#         ).update(status=LocalChangeLog.Status.ACKNOWLEDGED)
#         print(f"Marked {len(acknowledged_events)} sent items as fully acknowledged.")

#     print("\nPhase 2: Sending local changes to central server...")
#     logs_to_send = LocalChangeLog.objects.filter(
#         Q(status=LocalChangeLog.Status.PENDING)
#         | Q(status=LocalChangeLog.Status.FAILED),
#         retry_count__lt=MAX_RETRIES,
#     )

#     if not logs_to_send.exists():
#         print("No local changes to send.")
#         print("Sync cycle complete.")
#         return

#     payload = []
#     for log in logs_to_send:
#         model_class = log.content_type.model_class()
#         model_label = f"{model_class._meta.app_label}.{model_class.__name__}"
#         payload.append(
#             {
#                 "event_uuid": str(log.event_uuid),
#                 "model": model_label,
#                 "object_id": str(log.object_id),
#                 "action": log.action,
#                 "data_payload": log.data_payload,
#             }
#         )

#     print(f"Pushing {len(payload)} local changes...")
#     success, response = api_client.push_changes(payload)

#     if success:
#         logs_to_send.update(status=LocalChangeLog.Status.SENT, retry_count=0)
#         print("Successfully pushed changes. Marked as 'Sent'.")
#     else:
#         logs_to_send.update(
#             status=LocalChangeLog.Status.FAILED,
#             error_message=str(response),
#             retry_count=F("retry_count") + 1,
#         )
#         print(
#             f"Failed to push changes. Marked as 'Failed' and retry count incremented. Error: {response}"
#         )

#     print("Sync cycle complete.")
# ```
# #orcSync/serializers/generic.py
# ```
# import base64
# import decimal
# import uuid

# from django.db import models
# from django.db.models.fields.related import ManyToManyField
# from rest_framework import serializers


# class GenericModelSerializer(serializers.ModelSerializer):
#     """
#     A dynamic serializer that can serialize any Django model instance.
#     Correctly handles special types and now skips ManyToManyFields.
#     """

#     def to_representation(self, instance):
#         ret = {}
#         fields = instance._meta.get_fields()

#         for field in fields:
#             if isinstance(
#                 field,
#                 (
#                     models.ManyToOneRel,
#                     models.ManyToManyRel,
#                     models.OneToOneRel,
#                     ManyToManyField,
#                 ),
#             ):
#                 continue

#             value = getattr(instance, field.name)
#             if value is None:
#                 ret[field.name] = None
#                 continue
#             if isinstance(field, (models.DateTimeField, models.DateField)):
#                 ret[field.name] = value.isoformat()
#             elif isinstance(field, models.DecimalField):
#                 ret[field.name] = str(value)
#             elif isinstance(field, models.UUIDField):
#                 ret[field.name] = str(value)
#             elif isinstance(field, models.FileField):
#                 if value:
#                     try:
#                         with value.open("rb") as f:
#                             encoded_string = base64.b64encode(f.read()).decode("utf-8")
#                         ret[field.name] = {
#                             "filename": value.name.split("/")[-1],
#                             "content": encoded_string,
#                         }
#                     except (IOError, FileNotFoundError):
#                         ret[field.name] = None
#                 else:
#                     ret[field.name] = None
#             elif isinstance(field, models.ForeignKey):
#                 related_obj = value
#                 ret[field.attname] = str(related_obj.pk) if related_obj else None
#             else:
#                 ret[field.name] = value
#         return ret

#     class Meta:
#         pass

# ```
# #orcSync/apps.py
# ```

# from django.apps import AppConfig
# from django.conf import settings
# from django.db.models.signals import post_save, pre_delete


# class OrcsyncConfig(AppConfig):
#     default_auto_field = "django.db.models.BigAutoField"
#     name = "orcSync"

#     def ready(self):
#         """
#         This method is called once when Django starts.
#         It connects the signals for all models defined in settings.
#         """
#         from django.apps import apps

#         from .signals import handle_delete, handle_save

#         model_strings = getattr(settings, "SYNCHRONIZABLE_MODELS", [])
#         if not model_strings:
#             print("SYNC: No models configured for synchronization.")
#             return

#         for model_string in model_strings:
#             try:
#                 model = apps.get_model(model_string)

#                 post_save.connect(
#                     handle_save,
#                     sender=model,
#                     dispatch_uid=f"sync_save_{model._meta.label}",
#                 )

#                 pre_delete.connect(
#                     handle_delete,
#                     sender=model,
#                     dispatch_uid=f"sync_delete_{model._meta.label}",
#                 )

#                 print(f"SYNC: Signals connected for model {model_string}")

#             except LookupError:
#                 print(
#                     f"SYNC WARNING: Model '{model_string}' in SYNCHRONIZABLE_MODELS not found."
#                 )

# ```
# #orcSync/signals.py
# ```
# from django.contrib.contenttypes.models import ContentType

# from orcSync.models import LocalChangeLog
# from orcSync.serializers import GenericModelSerializer


# def create_log_entry(instance, action):
#     """
#     A generic function to serialize a model instance and create a LocalChangeLog entry.
#     """

#     class DynamicSerializer(GenericModelSerializer):
#         class Meta:
#             model = instance.__class__
#             fields = "__all__"

#     serializer = DynamicSerializer(instance)

#     LocalChangeLog.objects.create(
#         content_type=ContentType.objects.get_for_model(instance.__class__),
#         object_id=str(instance.pk),
#         action=action,
#         data_payload=serializer.data,
#     )
#     print(f"SYNC: Logged '{action}' for {instance.__class__.__name__} {instance.pk}")


# def handle_save(sender, instance, created, **kwargs):
#     """
#     A single receiver for the post_save signal.
#     """
#     if hasattr(instance, "_is_sync_operation") and instance._is_sync_operation:
#         return

#     action = "C" if created else "U"
#     create_log_entry(instance, action)


# def handle_delete(sender, instance, **kwargs):
#     """
#     A single receiver for the pre_delete signal.
#     We use pre_delete because the instance still exists in the database,
#     which is necessary for serialization.
#     """
#     if hasattr(instance, "_is_sync_operation") and instance._is_sync_operation:
#         return

#     create_log_entry(instance, "D")

# ```
# #orcSync/task.py
# ```
# import logging

# from celery import shared_task  # FIXED

# from orcSync.functions.orchestrator import run_sync_cycle

# logging.basicConfig(
#     filename="/app/logs/celery.log",
#     level=logging.INFO,
#     format="%(asctime)s - %(levelname)s - %(message)s",
# )


# @shared_task
# def run_sync_task():
#     logging.info("Starting sync cycle ****************")
#     try:
#         run_sync_cycle()
#         logging.info("Sync cycle finished successfully")
#     except Exception as e:
#         logging.error("ERROR during sync cycle", exc_info=True)

# ```
# #InsaBackednLatest/settings.py
# ```
# import os
# from datetime import timedelta
# from pathlib import Path  # Ensure this import exists

# from celery.schedules import crontab
# from decouple import config
# from dotenv import load_dotenv

# # Load environment variables from .env file
# load_dotenv()

# # Build paths inside the project like this: BASE_DIR / 'subdir'.
# BASE_DIR = Path(__file__).resolve().parent.parent

# # SECURITY WARNING: keep the secret key used in production secret!
# SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY")
# # SECURITY WARNING: don't run with debug turned on in production!
# # DEBUG = os.environ.get("DJANGO_DEBUG", "False") == "False"
# DEBUG = True
# ROOT_URLCONF = "InsaBackednLatest.urls"
# # Internationalization
# LANGUAGE_CODE = "en-us"
# USE_I18N = True
# # Internationalization
# LANGUAGE_CODE = "en-us"
# TIME_ZONE = "UTC"
# USE_I18N = True
# USE_TZ = True
# ALLOWED_HOSTS = os.environ.get("DJANGO_ALLOWED_HOSTS", "").split(",")
# TEMPLATES = [
#     {
#         "BACKEND": "django.template.backends.django.DjangoTemplates",
#         "DIRS": [os.path.join(BASE_DIR, "templates")],
#         "APP_DIRS": True,
#         "OPTIONS": {
#             "context_processors": [
#                 "django.template.context_processors.debug",
#                 "django.template.context_processors.request",
#                 "django.contrib.auth.context_processors.auth",
#                 "django.contrib.messages.context_processors.messages",
#             ],
#         },
#     },
# ]


# # Custom user model
# AUTH_USER_MODEL = "users.CustomUser"
# AUTHENTICATION_BACKENDS = [
#     "django.contrib.auth.backends.ModelBackend",
# ]

# # Database
# DATABASES = {
#     "default": {
#         "ENGINE": "django.db.backends.postgresql",
#         "NAME": os.environ.get("POSTGRES_DB"),
#         "USER": os.environ.get("POSTGRES_USER"),
#         "PASSWORD": os.environ.get("POSTGRES_PASSWORD"),
#         "HOST": os.environ.get("POSTGRES_HOST"),
#         "PORT": os.environ.get("POSTGRES_PORT"),
#     },
#     "central": {
#         "ENGINE": "django.db.backends.postgresql",
#         "NAME": os.environ.get("POSTGRES_DB"),
#         "USER": os.environ.get("POSTGRES_USER"),
#         "PASSWORD": os.environ.get("POSTGRES_PASSWORD"),
#         "HOST": "local_postgres",
#         "PORT": 5432,
#     },
# }


# # Email settings
# EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
# EMAIL_HOST = "smtp.gmail.com"
# EMAIL_PORT = os.environ.get("EMAIL_PORT")
# EMAIL_USE_TLS = os.environ.get("EMAIL_USE_TLS", "True") == "True"
# EMAIL_HOST_USER = os.environ.get("EMAIL_HOST_USER")
# EMAIL_HOST_PASSWORD = os.environ.get("EMAIL_HOST_PASSWORD")
# WSGI_APPLICATION = "InsaBackednLatest.wsgi.application"
# CORS_ALLOW_CREDENTIALS = os.environ.get("CORS_ALLOW_CREDENTIALS") == "True"
# CORS_ALLOW_HEADERS = os.environ.get("CORS_ALLOW_HEADERS", "").split(",")
# ALLOWED_HOSTS.append("*")
# CORS_ALLOW_METHODS = os.environ.get("CORS_ALLOW_METHODS", "").split(",")

# CORS_ALLOW_METHODS.extend(["OPTIONS", "GET", "POST", "PUT", "DELETE"])
# # JWT settings
# SIMPLE_JWT = {
#     "ACCESS_TOKEN_LIFETIME": timedelta(
#         minutes=int(os.environ.get("JWT_ACCESS_TOKEN_LIFETIME", "15"))
#     ),
#     "REFRESH_TOKEN_LIFETIME": timedelta(
#         days=int(os.environ.get("JWT_REFRESH_TOKEN_LIFETIME", "1"))
#     ),
#     "SIGNING_KEY": SECRET_KEY,
#     "VERIFYING_KEY": os.environ.get("JWT_VERIFYING_KEY", SECRET_KEY),
#     "AUTH_HEADER_TYPES": ("Bearer",),
# }

# INSTALLED_APPS = [
#     "django.contrib.admin",
#     "django.contrib.auth",
#     "django.contrib.contenttypes",
#     "django.contrib.sessions",
#     "django.contrib.messages",
#     "django.contrib.staticfiles",
#     "rest_framework",
#     "rest_framework_api_key",
#     "rest_framework.authtoken",
#     "django_filters",
#     "corsheaders",
#     "auditlog",
#     "django_crontab",
#     # Moved to correct position
#     "users",
#     "address",
#     "drivers",
#     "workstations",
#     "trucks",
#     "declaracions",
#     "exporters",
#     "tax",
#     "analysis",
#     "drf_yasg",
#     "django_pandas",
#     "core",
#     "localcheckings",
#     "audit",
#     "path",
#     "news",
#     "api",
#     "orcSync",
#     "django_celery_beat",
# ]

# MIDDLEWARE = [
#     "corsheaders.middleware.CorsMiddleware",
#     "django.middleware.security.SecurityMiddleware",
#     "django.contrib.sessions.middleware.SessionMiddleware",
#     "django.middleware.common.CommonMiddleware",
#     "django.middleware.csrf.CsrfViewMiddleware",
#     "django.contrib.auth.middleware.AuthenticationMiddleware",
#     "django.contrib.messages.middleware.MessageMiddleware",
#     "django.middleware.clickjacking.XFrameOptionsMiddleware",
#     "common.middleware.AttachJWTTokenMiddleware",
#     "common.middleware.RefreshTokenMiddleware",
#     "common.middleware.DisplayCurrentUserMiddleware",
# ]
# # External APIs and Tokens
# DERASH_API_KEY = os.environ.get("DERASH_API_KEY")
# DERASH_SECRET_KEY = os.environ.get("DERASH_SECRET_KEY")
# DERASH_END_POINT = os.environ.get("DERASH_END_POINT")
# WEIGHTBRIDGE_TOKEN = os.environ.get("WEIGHTBRIDGE_TOKEN")
# EXTERNAL_URI_WEIGHT_BRIDGE = os.environ.get("EXTERNAL_URI_WEIGHT_BRIDGE")
# STATIC_URL = "/static/"
# # CORS and CSRF settings
# CORS_ALLOWED_ORIGINS = os.environ.get("CORS_ALLOWED_ORIGINS", "").split(",")
# CSRF_TRUSTED_ORIGINS = os.environ.get("CSRF_TRUSTED_ORIGINS", "").split(",")

# # Media settings
# MEDIA_ROOT = os.environ.get("MEDIA_ROOT", "/app/media")
# MEDIA_URL = os.environ.get("MEDIA_URL", "/media/")

# STATIC_ROOT = BASE_DIR / "staticfiles"

# STATICFILES_DIRS = [
#     BASE_DIR / "static",
# ]


# SYNCHRONIZABLE_MODELS = [
#     "drivers.Driver",
#     "workstations.WorkStation",
#     "workstations.WorkedAt",
#     "trucks.TruckOwner",
#     "trucks.Truck",
#     "exporters.TaxPayerType",
#     "exporters.Exporter",
#     "tax.Tax",
#     "users.Report",
#     "users.UserStatus",
#     "users.CustomUser",
#     "users.Department",
# ]

# DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# # CRONJOBS = [("* * * * *", "orcSync.cron.run_sync", ">> /app/logs/cron.log 2>&1")]


# # Redis as broker and backend
# # CELERY_BROKER_URL = config("CELERY_BROKER_URL", default="redis://localhost:6379/0")
# # CELERY_RESULT_BACKEND = config(
# #     "CELERY_RESULT_BACKEND", default="redis://localhost:6379/1"
# # )

# CELERY_BROKER_URL = config("CELERY_BROKER_URL", default="redis://redis:6379/0")
# CELERY_RESULT_BACKEND = config("CELERY_RESULT_BACKEND", default="redis://redis:6379/1")


# # Enable task acknowledgment and retries
# CELERY_TASK_ACKS_LATE = True
# CELERY_TASK_RETRY_POLICY = {
#     "max_retries": 5,
#     "interval_start": 5,  # 5 seconds initial delay
#     "interval_step": 1,  # increase by 30s
#     "interval_max": 300,  # up to 5 minutes
# }

# # Periodic sync schedule
# CELERY_BEAT_SCHEDULE = {
#     "sync-with-central": {
#         "task": "orcSync.tasks.run_sync_task",
#         "schedule": crontab(minute="*/1"),  # Every 5 minutes
#     },
# }

# ```
