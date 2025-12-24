from django.conf import (  # Import settings to get AUTH_USER_MODEL if needed, though CustomUser is directly imported
    settings,
)
from django.db.models.signals import post_delete, post_save, pre_save
from django.dispatch import receiver

from .models import CustomUser


@receiver(pre_save, sender=CustomUser)
def delete_old_profile_image(sender, instance, **kwargs):
    """Delete old profile image if it's being replaced."""
    if not instance.pk:
        return

    try:
        old_instance = sender.objects.get(pk=instance.pk)
    except sender.DoesNotExist:
        return

    old_image = old_instance.profile_image
    new_image = instance.profile_image

    if old_image and old_image != new_image:
        old_image.delete(save=False)


@receiver(post_delete, sender=CustomUser)
def delete_profile_image_on_delete(sender, instance, **kwargs):
    """Delete profile image when user is deleted."""
    if instance.profile_image:
        instance.profile_image.delete(save=False)


@receiver(post_save, sender=CustomUser)
def sync_role_with_group(sender, instance, **kwargs):
    """
    Ensure user.groups is always synced with role.
    """
    instance.groups.clear()
    if instance.role:
        instance.groups.add(instance.role)
