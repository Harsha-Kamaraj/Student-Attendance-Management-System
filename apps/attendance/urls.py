from django.urls import path

from . import views

urlpatterns = [
    path("mark/", views.attendance_mark, name="attendance_mark"),
    path("mine/", views.attendance_summary, name="attendance_summary"),
]
