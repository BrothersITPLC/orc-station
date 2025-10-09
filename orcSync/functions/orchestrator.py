import base64

import requests
from django.apps import apps
from django.core.files.base import ContentFile
from django.db import IntegrityError, models, transaction
from django.db.models import F, Q
from django.db.models.signals import post_save, pre_delete

from orcSync.models import LocalChangeLog

from .client import CentralAPIClient

MAX_RETRIES = 5


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


def _apply_server_changes(changes, api_client):
    applied_event_ids_batch = []
    batch_size = 10

    from orcSync.signals import handle_delete, handle_save

    for i, change in enumerate(changes):
        model_label = change["model"]
        object_id = change["object_id"]
        action = change["action"]
        payload = change["data_payload"]

        try:
            Model = apps.get_model(model_label)

            post_save.disconnect(
                handle_save, sender=Model, dispatch_uid=f"sync_save_{Model._meta.label}"
            )
            pre_delete.disconnect(
                handle_delete,
                sender=Model,
                dispatch_uid=f"sync_delete_{Model._meta.label}",
            )

            with transaction.atomic():
                if action in ("C", "U"):
                    file_urls, data_fields = {}, {}
                    for field_name, value in payload.items():
                        if not hasattr(Model, field_name):
                            continue
                        field_obj = Model._meta.get_field(field_name)
                        if (
                            isinstance(field_obj, models.FileField)
                            and isinstance(value, str)
                            and value.startswith("http")
                        ):
                            file_urls[field_name] = value
                        else:
                            data_fields[field_name] = value

                    try:
                        # Try normal update_or_create by PK
                        instance, created = Model.objects.update_or_create(
                            pk=object_id, defaults=data_fields
                        )
                    except IntegrityError:
                        # Conflict: find the instance using unique fields
                        unique_fields = [
                            f.name
                            for f in Model._meta.fields
                            if f.unique and f.name in data_fields
                        ]
                        filter_kwargs = {f: data_fields[f] for f in unique_fields}
                        existing_instance = Model.objects.filter(
                            **filter_kwargs
                        ).first()
                        if existing_instance:
                            # Compare incoming vs existing (optional: by updated_at)
                            if "updated_at" in data_fields:
                                incoming_updated = data_fields["updated_at"]
                                existing_updated = getattr(
                                    existing_instance, "updated_at", None
                                )
                                if (
                                    not existing_updated
                                    or incoming_updated > existing_updated
                                ):
                                    for key, val in data_fields.items():
                                        setattr(existing_instance, key, val)
                                    existing_instance.save()
                                instance = existing_instance
                            else:
                                # Just apply fields as they are
                                for key, val in data_fields.items():
                                    setattr(existing_instance, key, val)
                                existing_instance.save()
                                instance = existing_instance
                        else:
                            # If no existing instance, re-raise the error
                            raise

                    # Handle file fields
                    for field_name, url in file_urls.items():
                        try:
                            response = requests.get(url, stream=True)
                            response.raise_for_status()
                            filename = url.split("/")[-1]
                            getattr(instance, field_name).save(
                                filename, ContentFile(response.content), save=True
                            )
                        except requests.RequestException as e:
                            print(
                                f"SYNC ERROR: Failed to download file for {object_id} from {url}. Error: {e}"
                            )

                elif action == "D":
                    instance_to_delete = Model.objects.filter(pk=object_id).first()
                    if instance_to_delete:
                        instance_to_delete._is_sync_operation = True
                        instance_to_delete.delete()

            applied_event_ids_batch.append(change["id"])

        except LookupError:
            print(
                f"SYNC WARNING: Model {model_label} not found locally. Skipping change."
            )
        except Exception as e:
            print(f"SYNC ERROR: Failed applying change {change['id']}: {e}. Skipping.")
        finally:
            post_save.connect(
                handle_save, sender=Model, dispatch_uid=f"sync_save_{Model._meta.label}"
            )
            pre_delete.connect(
                handle_delete,
                sender=Model,
                dispatch_uid=f"sync_delete_{Model._meta.label}",
            )

        # Batch acknowledge
        if len(applied_event_ids_batch) >= batch_size or (i + 1) == len(changes):
            print(
                f"Acknowledging batch of {len(applied_event_ids_batch)} applied changes..."
            )
            success, _ = api_client.acknowledge_changes(applied_event_ids_batch)
            if not success:
                print(
                    "SYNC WARNING: Failed to acknowledge batch. These changes may be re-downloaded later."
                )
            applied_event_ids_batch = []


def run_sync_cycle():
    """
    Executes the full "receive-first, send-second" synchronization cycle.
    This is the main function to call to trigger a sync.
    """
    print("Starting sync cycle...")
    api_client = CentralAPIClient()

    print("Phase 1: Receiving changes from central server...")
    server_data = api_client.get_pending_changes()

    if server_data is None:
        print("Sync cycle failed: Could not connect to central server.")
        return

    pending_changes = server_data.get("pending_changes", [])
    if pending_changes:
        print(f"Applying {len(pending_changes)} server changes...")
        _apply_server_changes(pending_changes, api_client)
    else:
        print("No pending changes to apply from server.")

    acknowledged_events = server_data.get("acknowledged_events", [])
    if acknowledged_events:
        LocalChangeLog.objects.filter(
            event_uuid__in=acknowledged_events, status=LocalChangeLog.Status.SENT
        ).update(status=LocalChangeLog.Status.ACKNOWLEDGED)
        print(f"Marked {len(acknowledged_events)} sent items as fully acknowledged.")

    print("\nPhase 2: Sending local changes to central server...")
    logs_to_send = LocalChangeLog.objects.filter(
        Q(status=LocalChangeLog.Status.PENDING)
        | Q(status=LocalChangeLog.Status.FAILED),
        retry_count__lt=MAX_RETRIES,
    )

    if not logs_to_send.exists():
        print("No local changes to send.")
        print("Sync cycle complete.")
        return

    payload = []
    for log in logs_to_send:
        model_class = log.content_type.model_class()
        model_label = f"{model_class._meta.app_label}.{model_class.__name__}"
        payload.append(
            {
                "event_uuid": str(log.event_uuid),
                "model": model_label,
                "object_id": str(log.object_id),
                "action": log.action,
                "data_payload": log.data_payload,
            }
        )

    print(f"Pushing {len(payload)} local changes...")
    success, response = api_client.push_changes(payload)

    if success:
        logs_to_send.update(status=LocalChangeLog.Status.SENT, retry_count=0)
        print("Successfully pushed changes. Marked as 'Sent'.")
    else:
        logs_to_send.update(
            status=LocalChangeLog.Status.FAILED,
            error_message=str(response),
            retry_count=F("retry_count") + 1,
        )
        print(
            f"Failed to push changes. Marked as 'Failed' and retry count incremented. Error: {response}"
        )

    print("Sync cycle complete.")
