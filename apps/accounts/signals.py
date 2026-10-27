from django.contrib.auth.signals import user_logged_in
from django.dispatch import receiver

from .otp import SESSION_SETUP_SECRET, SESSION_VERIFIED


@receiver(user_logged_in)
def require_fresh_otp(sender, request, **kwargs):
    """Every password login, including Django admin reauthentication, needs a fresh code."""
    request.session.pop(SESSION_VERIFIED, None)
    request.session.pop(SESSION_SETUP_SECRET, None)
