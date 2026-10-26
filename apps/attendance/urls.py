from django.urls import path

from . import correction_views, history_views, views

urlpatterns = [
    path("mark/", views.attendance_mark, name="attendance_mark"),
    path("mine/", views.attendance_summary, name="attendance_summary"),
    path("threshold/", views.threshold_settings, name="threshold_settings"),
    path("history/", history_views.attendance_history, name="attendance_history"),
    path("records/<int:pk>/changes/", history_views.attendance_changes, name="attendance_changes"),
    path("records/<int:pk>/correct/", correction_views.attendance_correct, name="attendance_correct"),
    path(
        "correction-window/", correction_views.correction_window_settings, name="correction_window_settings"
    ),
]
