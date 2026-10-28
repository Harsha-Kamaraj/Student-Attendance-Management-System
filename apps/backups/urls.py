from django.urls import path

from . import views

urlpatterns = [
    path("", views.backup_list, name="backup_list"),
    path("create/", views.backup_create, name="backup_create"),
    path("schedule/", views.backup_schedule, name="backup_schedule"),
    path("import/", views.backup_import, name="backup_import"),
    path("<uuid:pk>/download/", views.backup_download, name="backup_download"),
    path("<uuid:pk>/restore/", views.backup_restore, name="backup_restore"),
]
