from django.urls import path

from . import views

urlpatterns = [
    path("sections/", views.section_list, name="section_list"),
    path("sections/create/", views.section_create, name="section_create"),
    path("sections/<int:pk>/", views.section_detail, name="section_detail"),
    path("sections/<int:pk>/enroll/", views.enrollment_create, name="enrollment_create"),
    path("sections/<int:pk>/classes/add/", views.class_assign, name="class_assign"),
    path(
        "sections/<int:pk>/classes/<int:assignment_pk>/teacher/",
        views.class_teacher,
        name="class_teacher",
    ),
    path("my-classes/", views.my_classes, name="my_classes"),
    path(
        "sections/<int:pk>/enrollments/<int:enrollment_pk>/remove/",
        views.enrollment_remove,
        name="enrollment_remove",
    ),
    path("faculty/", views.faculty_list, name="faculty_list"),
    path("faculty/create/", views.faculty_create, name="faculty_create"),
    path("faculty/<int:pk>/", views.faculty_detail, name="faculty_detail"),
    path("faculty/<int:pk>/edit/", views.faculty_edit, name="faculty_edit"),
    path("faculty/<int:pk>/deactivate/", views.faculty_deactivate, name="faculty_deactivate"),
    path("faculty/<int:pk>/reactivate/", views.faculty_reactivate, name="faculty_reactivate"),
    path("faculty/<int:pk>/delete/", views.faculty_delete, name="faculty_delete"),
    path("students/", views.student_list, name="student_list"),
    path("students/create/", views.student_create, name="student_create"),
    path("students/<int:pk>/", views.student_detail, name="student_detail"),
    path("students/<int:pk>/edit/", views.student_edit, name="student_edit"),
    path("students/<int:pk>/deactivate/", views.student_deactivate, name="student_deactivate"),
    path("students/<int:pk>/reactivate/", views.student_reactivate, name="student_reactivate"),
    path("students/<int:pk>/delete/", views.student_delete, name="student_delete"),
    path("subjects/", views.subject_list, name="subject_list"),
    path("subjects/create/", views.subject_create, name="subject_create"),
    path("subjects/<int:pk>/", views.subject_detail, name="subject_detail"),
    path("subjects/<int:pk>/edit/", views.subject_edit, name="subject_edit"),
    path("subjects/<int:pk>/delete/", views.subject_delete, name="subject_delete"),
    path("subjects/<int:pk>/offer/", views.subject_offer, name="subject_offer"),
    path(
        "subjects/<int:pk>/offerings/<int:assignment_pk>/withdraw/",
        views.subject_withdraw,
        name="subject_withdraw",
    ),
]
