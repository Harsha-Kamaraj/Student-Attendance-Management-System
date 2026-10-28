from django.core.paginator import Paginator
from django.shortcuts import render
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET

from apps.accounts.models import Role
from apps.accounts.permissions import requires
from apps.attendance.models import AttendanceThreshold

from .models import Notification
from .services import shortage_list_for


@never_cache
@require_GET
@requires("notifications.view")
def notification_list(request):
    """The signed-in user's own notifications only (SEC-25). Viewing marks them as read."""
    notifications = Notification.objects.filter(recipient=request.user)
    page = Paginator(notifications, 25).get_page(request.GET.get("page"))
    unread_ids = [n.pk for n in page if n.read_at is None]
    response = render(request, "notifications/list.html", {"page_obj": page, "unread_ids": set(unread_ids)})
    if unread_ids:
        Notification.objects.filter(pk__in=unread_ids, recipient=request.user).update(read_at=timezone.now())
    return response


@never_cache
@require_GET
@requires("low_attendance.view")
def shortage_list(request):
    """Students currently below the threshold: Admin all, Faculty own subjects (BL-24, AR-14).

    Computed from saved records on every request, so new attendance, corrections and
    threshold changes show immediately and recovered students drop off.
    """
    threshold = AttendanceThreshold.current_value()
    overall_rows, subject_rows = shortage_list_for(request.user, threshold)
    return render(
        request,
        "notifications/shortage_list.html",
        {
            "threshold": threshold,
            "overall_rows": overall_rows,
            "subject_rows": subject_rows,
            "show_overall": request.user.role == Role.ADMIN,
            "generated_at": timezone.localtime(),
        },
    )
