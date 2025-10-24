import uuid

from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.db import models

from base.models import BaseModel
from workstations.models import WorkStation


class CentralServerCredential(BaseModel):
    """
    A singleton model to store this workstation's own identity and the
    connection details for the one central server it syncs with.

    Only one instance of this model should ever exist.
    """

    location = models.OneToOneField(
        WorkStation, related_name="sync_credential", on_delete=models.CASCADE
    )
    base_url = models.CharField(
        max_length=255,
        help_text="The base URL of the central server's API. E.g., https://api.mycompany.com",
    )
    api_key = models.CharField(
        max_length=255, help_text="The secret API key assigned to this workstation."
    )

    def __str__(self):
        return f"Credentials for Central Server ({self.base_url})"

    def save(self, *args, **kwargs):
        """
        Overrides the save method to ensure only one instance can be created.
        """
        if not self.pk and CentralServerCredential.objects.exists():
            raise ValidationError(
                "Only one CentralServerCredential instance can be created."
            )
        return super().save(*args, **kwargs)


class LocalChangeLog(BaseModel):
    """
    Logs all local Create, Update, and Delete operations that need to be
    pushed to the central server. This acts as a resilient "outbox".
    """

    class Action(models.TextChoices):
        CREATED = "C", "Created"
        UPDATED = "U", "Updated"
        DELETED = "D", "Deleted"

    class Status(models.TextChoices):
        PENDING = "P", "Pending"
        SENT = "S", "Sent"
        FAILED = "F", "Failed"
        ACKNOWLEDGED = (
            "A",
            "Acknowledged",
        )

    id = models.BigAutoField(primary_key=True)
    event_uuid = models.UUIDField(
        default=uuid.uuid4,
        editable=False,
        unique=True,
        help_text="Unique ID for this event, sent to the server for acknowledgement.",
    )

    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.CharField(max_length=255)
    changed_object = GenericForeignKey("content_type", "object_id")
    retry_count = models.PositiveIntegerField(
        default=0, help_text="Number of times this entry has failed to sync."
    )
    action = models.CharField(max_length=1, choices=Action.choices)
    data_payload = models.JSONField(
        help_text="A JSON snapshot of the model's data to be sent."
    )

    status = models.CharField(
        max_length=1, choices=Status.choices, default=Status.PENDING, db_index=True
    )

    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    sent_at = models.DateTimeField(
        null=True, blank=True, help_text="Timestamp of the last push attempt."
    )
    error_message = models.TextField(
        blank=True, null=True, help_text="Stores the error response if a push fails."
    )

    class Meta:
        ordering = ["timestamp"]

    def __str__(self):
        return f"[{self.get_status_display()}] {self.get_action_display()} on {self.content_type.model} @ {self.timestamp}"


class ZoimeIntegrationConfig(BaseModel):
    """
    A singleton model to store the configuration and authentication details
    for the Zoime third-party API integration on this workstation.
    Only one instance of this model should ever exist.
    """

    is_enabled = models.BooleanField(
        default=False, help_text="Enable or disable synchronization with the Zoime API."
    )
    base_url = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="The base URL for the Zoime third-party API. E.g., http://localhost:7000/ZOIME-WBS",
    )
    auth_token = models.TextField(
        blank=True,
        null=True,
        help_text="Current valid Bearer token for Zoime API. This token must be manually obtained and updated.",
    )

    class Meta:
        verbose_name = "Zoime Integration Configuration"
        verbose_name_plural = "Zoime Integration Configurations"

    def __str__(self):
        return (
            f"Zoime API Configuration ({'Enabled' if self.is_enabled else 'Disabled'})"
        )

    def save(self, *args, **kwargs):
        """
        Overrides the save method to ensure only one instance can be created.
        """
        if not self.pk and ZoimeIntegrationConfig.objects.exists():
            raise ValidationError(
                "Only one ZoimeIntegrationConfig instance can be created."
            )
        return super().save(*args, **kwargs)


class ZoimeUserSyncStatus(BaseModel):
    """
    Tracks the synchronization status of a CustomUser with the Zoime API.
    Does not modify the CustomUser model directly.
    """

    zoime_incremental_id = models.PositiveIntegerField(
        unique=True,
        db_index=True,
        editable=False,
        null=True,
        help_text="An auto-incrementing integer for mapping to the Zoime system.",
    )
    user = models.OneToOneField(
        "users.CustomUser",
        on_delete=models.CASCADE,
        related_name="zoime_sync_status",
        help_text="The CustomUser instance this status refers to.",
    )
    zoime_password = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Plaintext password for the user in the Zoime application. WARNING: Storing plaintext passwords is a security risk.",
    )
    last_synced_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp of the last successful synchronization of this user's data to Zoime API.",
    )
    sync_attempted_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp of the last attempt to synchronize this user to Zoime API, regardless of success.",
    )
    last_error = models.TextField(
        blank=True,
        null=True,
        help_text="Stores the last error message if synchronization failed.",
    )

    class Meta:
        verbose_name = "Zoime User Sync Status"
        verbose_name_plural = "Zoime User Sync Statuses"
        ordering = ["user__username"]

    def save(self, *args, **kwargs):
        if self.zoime_incremental_id is None:
            last_id = ZoimeUserSyncStatus.objects.aggregate(
                models.Max("zoime_incremental_id")
            )["zoime_incremental_id__max"]
            self.zoime_incremental_id = (last_id or 0) + 1
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Zoime Sync for {self.user.username} (Last synced: {self.last_synced_at or 'Never'})"
