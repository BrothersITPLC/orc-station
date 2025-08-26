from django.contrib import admin

from .models import WorkedAt, WorkStation

# Register your models here.
admin.site.register(WorkStation)
admin.site.register(WorkedAt)
