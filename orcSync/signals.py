from django.contrib.contenttypes.models import ContentType

from orcSync.models import LocalChangeLog
from orcSync.serializers import GenericModelSerializer


def create_log_entry(instance, action):
    """
    A generic function to serialize a model instance and create a LocalChangeLog entry.
    """

    class DynamicSerializer(GenericModelSerializer):
        class Meta:
            model = instance.__class__
            fields = "__all__"

    serializer = DynamicSerializer(instance)

    LocalChangeLog.objects.create(
        content_type=ContentType.objects.get_for_model(instance.__class__),
        object_id=instance.pk,
        action=action,
        data_payload=serializer.data,
    )
    print(f"SYNC: Logged '{action}' for {instance.__class__.__name__} {instance.pk}")


def handle_save(sender, instance, created, **kwargs):
    """
    A single receiver for the post_save signal.
    """
    if hasattr(instance, "_is_sync_operation") and instance._is_sync_operation:
        return

    action = "C" if created else "U"
    create_log_entry(instance, action)


def handle_delete(sender, instance, **kwargs):
    """
    A single receiver for the pre_delete signal.
    We use pre_delete because the instance still exists in the database,
    which is necessary for serialization.
    """
    if hasattr(instance, "_is_sync_operation") and instance._is_sync_operation:
        return

    create_log_entry(instance, "D")
