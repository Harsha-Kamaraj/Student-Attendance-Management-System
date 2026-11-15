from django.contrib.auth.signals import user_logged_in
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from .models import User
from .otp import SESSION_SETUP_SECRET, SESSION_VERIFIED
from .sessions import end_user_sessions


@receiver(user_logged_in)
def require_fresh_otp(sender, request, **kwargs):
    """Every password login, including Django admin reauthentication, needs a fresh code."""
    request.session.pop(SESSION_VERIFIED, None)
    request.session.pop(SESSION_SETUP_SECRET, None)


@receiver(post_save, sender=User)
def end_sessions_when_deactivated(sender, instance, update_fields=None, raw=False, **kwargs):
    """A deactivated account is signed out everywhere and its session rows are deleted (D-03)."""
    if raw or instance.is_active or (update_fields is not None and "is_active" not in update_fields):
        return
    end_user_sessions(instance.pk)


@receiver(post_delete, sender=User)
def end_sessions_when_deleted(sender, instance, **kwargs):
    """A permanently deleted account leaves no session rows behind (D-04)."""
    end_user_sessions(instance.pk)
