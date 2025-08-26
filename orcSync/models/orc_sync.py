import uuid

from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.db import models

from workstations.models import WorkStation


class CentralServerCredential(models.Model):
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

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

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


class LocalChangeLog(models.Model):
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
    object_id = models.UUIDField()
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
