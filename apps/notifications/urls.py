from django.urls import path

from . import views

urlpatterns = [
    path("notifications/", views.notification_list, name="notification_list"),
    path("attendance/shortages/", views.shortage_list, name="shortage_list"),
]
