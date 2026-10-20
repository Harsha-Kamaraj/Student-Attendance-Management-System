from django.urls import path

from . import views

urlpatterns = [
    path("login/", views.LoginView.as_view(), name="login"),
    path("password/change/", views.PasswordChangeView.as_view(), name="password_change"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("dashboard/admin/", views.dashboard_admin, name="dashboard_admin"),
    path("dashboard/faculty/", views.dashboard_faculty, name="dashboard_faculty"),
    path("dashboard/student/", views.dashboard_student, name="dashboard_student"),
    path("users/", views.account_list, name="account_list"),
    path("users/create/", views.account_create, name="account_create"),
    path("users/<int:pk>/reset-password/", views.account_reset_password, name="account_reset_password"),
]
