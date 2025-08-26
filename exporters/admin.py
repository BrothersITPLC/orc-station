from django.contrib import admin

# Register your models here.
from .models import Exporter, TaxPayerType

admin.site.register(Exporter)
admin.site.register(TaxPayerType)
