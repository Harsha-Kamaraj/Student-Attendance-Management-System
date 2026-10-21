from django.urls import path

from . import views

urlpatterns = [
    path("students/", views.student_list, name="student_list"),
    path("students/create/", views.student_create, name="student_create"),
    path("students/<int:pk>/", views.student_detail, name="student_detail"),
    path("students/<int:pk>/edit/", views.student_edit, name="student_edit"),
    path("students/<int:pk>/deactivate/", views.student_deactivate, name="student_deactivate"),
    path("students/<int:pk>/reactivate/", views.student_reactivate, name="student_reactivate"),
    path("students/<int:pk>/delete/", views.student_delete, name="student_delete"),
]
