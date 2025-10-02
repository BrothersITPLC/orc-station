from django.contrib import admin

# Register your models here.
from orcSync.models import (
    CentralServerCredential,
    LocalChangeLog,
    ZoimeIntegrationConfig,
    ZoimeUserSyncStatus,
)

admin.site.register(CentralServerCredential)
admin.site.register(ZoimeIntegrationConfig)
admin.site.register(ZoimeUserSyncStatus)
admin.site.register(LocalChangeLog)
