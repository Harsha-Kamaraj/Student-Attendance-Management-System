from django.shortcuts import redirect
from django.urls import reverse


class ForcePasswordChangeMiddleware:
    """A user with a temporary password must change it before any other action (SEC-06)."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = request.user
        if user.is_authenticated and user.must_change_password:
            change_url = reverse("password_change")
            # Signing out must be possible even before the temporary password is changed.
            logout_url = reverse("logout")
            if request.path not in (change_url, logout_url) and not request.path.startswith("/static/"):
                return redirect(change_url)
        return self.get_response(request)
