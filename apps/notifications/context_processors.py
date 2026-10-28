from apps.accounts.models import Role

from .models import Notification


def unread_notifications(request):
    """Unread count for the navigation bar; only students receive notifications (BL-23)."""
    user = getattr(request, "user", None)
    if not (user and user.is_authenticated and user.role == Role.STUDENT):
        return {}
    return {"unread_notification_count": Notification.objects.filter(recipient=user, read_at=None).count()}
