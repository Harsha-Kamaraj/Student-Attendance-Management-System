from django.contrib import admin
from django.contrib.auth.decorators import login_not_required
from django.urls import include, path
from django.views.generic import TemplateView

handler403 = "apps.accounts.errors.permission_denied"

urlpatterns = [
    path("", login_not_required(TemplateView.as_view(template_name="home.html")), name="home"),
    path("", include("apps.accounts.urls")),
    path("", include("apps.academics.urls")),
    path("", include("apps.notifications.urls")),
    path("attendance/", include("apps.attendance.urls")),
    path("admin/", admin.site.urls),
]
