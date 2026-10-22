"""Attendance marking workflow (BL-12)."""

import logging
from urllib.parse import urlencode

from django.contrib import messages
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import DatabaseError, IntegrityError
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.cache import never_cache

from apps.academics.models import Enrollment, TeachingAssignment
from apps.accounts.models import Role
from apps.accounts.permissions import requires, visible_assignments

from .forms import AttendanceSelectionForm
from .models import AttendanceSession, Status
from .services import submit_attendance

logger = logging.getLogger(__name__)


def _deny_other_teachers(user, raw_pk):
    """Don't silently show a form error for an existing class outside the user's scope."""
    try:
        pk = int(raw_pk)
    except (TypeError, ValueError):
        return
    if (
        TeachingAssignment.objects.filter(pk=pk).exists()
        and not visible_assignments(user).filter(pk=pk).exists()
    ):
        raise PermissionDenied("Class is outside your teaching assignments.")


def _posted_statuses(post):
    statuses = {}
    for name, value in post.items():
        if not name.startswith("status_"):
            continue
        raw_id = name[7:]
        if (
            not raw_id.isascii()
            or not raw_id.isdecimal()
            or len(raw_id) > 19
            or str(int(raw_id)) != raw_id
            or not 0 < int(raw_id) <= 9223372036854775807
        ):
            raise ValidationError("An attendance status has an invalid student ID. Reload the roster.")
        student_id = int(raw_id)
        values = post.getlist(name) if hasattr(post, "getlist") else [value]
        if len(values) != 1 or student_id in statuses:
            raise ValidationError("Submit exactly one attendance status for each student.")
        if value not in Status.values:
            raise ValidationError("Each student must be marked Present or Absent.")
        statuses[student_id] = value
    return statuses


@never_cache
@requires("attendance.mark")
def attendance_mark(request):
    data = request.POST if request.method == "POST" else request.GET
    if data:
        _deny_other_teachers(request.user, data.get("assignment"))
    form = AttendanceSelectionForm(data or None, user=request.user)
    roster_rows = []
    existing_rows = []
    existing = None
    selected = None
    submitted = {}
    statuses_error = None
    if request.method == "POST":
        try:
            submitted = _posted_statuses(request.POST)
        except ValidationError as error:
            statuses_error = error

    if data and form.is_valid():
        selected = form.cleaned_data
        assignment = selected["assignment"]
        roster = (
            Enrollment.objects.filter(assignment=assignment, student__user__is_active=True)
            .select_related("student")
            .order_by("student__roll_number")
        )
        roster_rows = [
            {"student": row.student, "status": submitted.get(row.student_id, "")} for row in roster
        ]

        if request.method == "POST":
            try:
                if statuses_error is not None:
                    raise statuses_error
                session, created = submit_attendance(
                    actor=request.user,
                    assignment=assignment,
                    day=selected["date"],
                    period=selected["period"],
                    statuses=submitted,
                    reason=request.POST.get("reason", ""),
                )
            except ValidationError as error:
                form.add_error(None, error)
            except IntegrityError:
                form.add_error(None, "Concurrent attendance submission detected. Reload the class and retry.")
            except DatabaseError:
                logger.exception("Attendance submission failed")
                form.add_error(
                    None, "Attendance could not be saved. No changes were saved. Please try again."
                )
            else:
                if created:
                    messages.success(request, f"Attendance saved for {session}.")
                else:
                    messages.info(request, "This attendance was already saved. No duplicate was created.")
                query = urlencode(
                    {
                        "assignment": assignment.pk,
                        "date": selected["date"].isoformat(),
                        "period": selected["period"],
                    }
                )
                return redirect(f"{reverse('attendance_mark')}?{query}")

        existing = AttendanceSession.objects.filter(
            assignment=assignment, date=selected["date"], period=selected["period"]
        ).first()
        if existing:
            existing_rows = existing.records.select_related("student").order_by("student__roll_number")

    return render(
        request,
        "attendance/mark.html",
        {
            "form": form,
            "selected": selected,
            "roster_rows": roster_rows,
            "existing": existing,
            "existing_rows": existing_rows,
            "is_admin": request.user.role == Role.ADMIN,
        },
        status=400 if request.method == "POST" else 200,
    )
