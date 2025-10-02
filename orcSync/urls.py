from django.urls import include, path

from orcSync.views.zoime_sync import ZoimeUserSyncListView, ZoimeUserSyncTriggerView

urlpatterns = [
    path(
        "zoime-sync/users/",
        ZoimeUserSyncListView.as_view(),
        name="zoime-sync-user-list",
    ),
    path(
        "zoime-sync/users/<uuid:pk>/trigger/",
        ZoimeUserSyncTriggerView.as_view(),
        name="zoime-sync-user-trigger",
    ),
]
