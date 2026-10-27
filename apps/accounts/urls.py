from django.urls import path

from . import otp_views, views

urlpatterns = [
    path("login/", views.LoginView.as_view(), name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("password/change/", views.PasswordChangeView.as_view(), name="password_change"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("dashboard/admin/", views.dashboard_admin, name="dashboard_admin"),
    path("dashboard/faculty/", views.dashboard_faculty, name="dashboard_faculty"),
    path("dashboard/student/", views.dashboard_student, name="dashboard_student"),
    path("users/", views.account_list, name="account_list"),
    path("users/create/", views.account_create, name="account_create"),
    path("users/<int:pk>/reset-password/", views.account_reset_password, name="account_reset_password"),
    path("users/<int:pk>/reset-otp/", otp_views.account_reset_otp, name="account_reset_otp"),
    path("otp/setup/", otp_views.otp_setup, name="otp_setup"),
    path("otp/verify/", otp_views.otp_verify, name="otp_verify"),
    path("otp/email/", otp_views.otp_email, name="otp_email"),
]
