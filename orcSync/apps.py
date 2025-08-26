# from django.apps import AppConfig


# class OrcsyncConfig(AppConfig):
#     default_auto_field = 'django.db.models.BigAutoField'
#     name = 'orcSync'


from django.apps import AppConfig
from django.conf import settings
from django.db.models.signals import post_save, pre_delete


class OrcsyncConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "orcSync"

    def ready(self):
        """
        This method is called once when Django starts.
        It connects the signals for all models defined in settings.
        """
        from django.apps import apps

        from .signals import handle_delete, handle_save

        model_strings = getattr(settings, "SYNCHRONIZABLE_MODELS", [])
        if not model_strings:
            print("SYNC: No models configured for synchronization.")
            return

        for model_string in model_strings:
            try:
                model = apps.get_model(model_string)

                post_save.connect(
                    handle_save,
                    sender=model,
                    dispatch_uid=f"sync_save_{model._meta.label}",
                )

                pre_delete.connect(
                    handle_delete,
                    sender=model,
                    dispatch_uid=f"sync_delete_{model._meta.label}",
                )

                print(f"SYNC: Signals connected for model {model_string}")

            except LookupError:
                print(
                    f"SYNC WARNING: Model '{model_string}' in SYNCHRONIZABLE_MODELS not found."
                )
