from django.contrib import admin
from django.contrib.auth.models import Permission

from .models import CustomUser, Department, Report

# Register the Permission model


# Register your models here.
admin.site.register(CustomUser)
admin.site.register(Department)
admin.site.register(Report)
admin.site.register(Permission)
