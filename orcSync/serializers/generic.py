import base64
import decimal
import uuid

from django.db import models
from django.db.models.fields.related import ManyToManyField
from rest_framework import serializers


class GenericModelSerializer(serializers.ModelSerializer):
    """
    A dynamic serializer that can serialize any Django model instance.
    Correctly handles special types and now skips ManyToManyFields.
    """

    def to_representation(self, instance):
        ret = {}
        fields = instance._meta.get_fields()

        for field in fields:
            if isinstance(
                field,
                (
                    models.ManyToOneRel,
                    models.ManyToManyRel,
                    models.OneToOneRel,
                    ManyToManyField,
                ),
            ):
                continue

            value = getattr(instance, field.name)
            if value is None:
                ret[field.name] = None
                continue
            if isinstance(field, (models.DateTimeField, models.DateField)):
                ret[field.name] = value.isoformat()
            elif isinstance(field, models.DecimalField):
                ret[field.name] = str(value)
            elif isinstance(field, models.UUIDField):
                ret[field.name] = str(value)
            elif isinstance(field, models.FileField):
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
            elif isinstance(field, models.ForeignKey):
                related_obj = value
                ret[field.attname] = str(related_obj.pk) if related_obj else None
            else:
                ret[field.name] = value
        return ret

    class Meta:
        pass
