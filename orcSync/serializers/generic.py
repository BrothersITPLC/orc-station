import base64
import decimal
import uuid

from django.core.files.base import ContentFile
from django.db import models
from rest_framework import serializers


class GenericModelSerializer(serializers.ModelSerializer):
    """
    A dynamic serializer that can serialize any Django model instance.
    It automatically detects all fields, including relationships and files.
    Special types (datetime, decimal, uuid, files) are correctly converted.
    """

    def to_representation(self, instance):
        """Converts a model instance into a dictionary of primitives."""
        ret = {}
        fields = instance._meta.get_fields()

        for field in fields:
            if isinstance(
                field, (models.ManyToOneRel, models.ManyToManyRel, models.OneToOneRel)
            ):
                continue

            value = getattr(instance, field.name)
            if value is None:
                ret[field.name] = None
                continue

            if isinstance(field, (models.DateTimeField, models.DateField)):
                ret[field.name] = value.isoformat()
                continue

            if isinstance(field, models.DecimalField):
                ret[field.name] = str(value)
                continue
            if isinstance(field, models.UUIDField):
                ret[field.name] = str(value)
                continue

            if isinstance(field, (models.FileField, models.ImageField)):
                if value:
                    try:
                        with value.open("rb") as f:
                            encoded_string = base64.b64encode(f.read()).decode("utf-8")
                        ret[field.name] = {
                            "filename": value.name.split("/")[-1],
                            "content": encoded_string,
                        }
                    except (IOError, FileNotFoundError):
                        ret[field.name] = None
                else:
                    ret[field.name] = None
                continue

            if isinstance(field, models.ForeignKey):
                related_obj = getattr(instance, field.name)
                ret[field.attname] = str(related_obj.pk) if related_obj else None
                continue
            ret[field.name] = value

        return ret

    class Meta:
        pass
