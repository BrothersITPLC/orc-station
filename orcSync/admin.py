from django.contrib import admin

# Register your models here.
from orcSync.models import CentralServerCredential, LocalChangeLog

admin.site.register(CentralServerCredential)
admin.site.register(LocalChangeLog)
