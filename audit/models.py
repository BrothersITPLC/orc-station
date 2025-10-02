from django.db import models
from django.utils import timezone

from base.models import BaseModel
from users.models import CustomUser


class AuditLog(BaseModel):
    ACTION_CHOICES = [
        ("create", "Create"),
        ("update", "Update"),
        ("delete", "Delete"),
        ("custom", "Custom Action"),
    ]

    user = models.ForeignKey(
        CustomUser, on_delete=models.SET_NULL, null=True, blank=True
    )
    action = models.CharField(max_length=10, choices=ACTION_CHOICES)
    object_id = models.TextField()  # Store the primary key of the related object
    timestamp = models.DateTimeField(default=timezone.now)
    previous_snapshot = models.JSONField(
        null=True, blank=True
    )  # Previous state snapshot
    updated_snapshot = models.JSONField(null=True, blank=True)  # Updated state snapshot
    table_name = models.CharField(max_length=255)  # Store the model/table name
    description = models.TextField(null=True, blank=True)  # Custom description

    def __str__(self):
        return f"{self.user} {self.action} {self.table_name} (ID: {self.object_id})"
