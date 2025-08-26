from django.contrib.auth.models import Group
from django.db.models.signals import post_migrate
from django.dispatch import receiver


@receiver(post_migrate)
def create_default_groups(sender, **kwargs):
    if sender.name == "your_app":  # Ensure this runs only for your app
        groups = ["admin", "controller"]
        for group_name in groups:
            group, created = Group.objects.get_or_create(name=group_name)
            if created:
                print(f'Group "{group_name}" created.')
            else:
                print(f'Group "{group_name}" already exists.')
