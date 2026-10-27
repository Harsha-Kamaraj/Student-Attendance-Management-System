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
            # Signing out, and finishing two-factor login first (BL-33), must stay possible;
            # otherwise a new user would bounce between OTP setup and password change.
            allowed = {change_url} | {
                reverse(name) for name in ("logout", "otp_setup", "otp_verify", "otp_email")
            }
            if request.path not in allowed and not request.path.startswith("/static/"):
                return redirect(change_url)
        return self.get_response(request)


class OTPRequiredMiddleware:
    """After the password, a one-time code is required before any other page (SEC-29, SEC-30).

    Users who have not set up the authenticator app are sent to setup; others to the code page.
    Only the OTP pages and Log out are reachable until the code is accepted.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        from django.conf import settings

        from .otp import SESSION_VERIFIED

        user = request.user
        if settings.OTP_REQUIRED and user.is_authenticated and not request.session.get(SESSION_VERIFIED):
            allowed = {reverse(name) for name in ("otp_setup", "otp_verify", "otp_email", "logout")}
            if request.path not in allowed:
                return redirect("otp_verify" if user.otp_confirmed else "otp_setup")
        return self.get_response(request)
