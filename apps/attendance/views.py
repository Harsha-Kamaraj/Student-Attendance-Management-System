"""Attendance marking workflow (BL-12)."""

import logging
from urllib.parse import urlencode

from django.contrib import messages
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import DatabaseError, IntegrityError, transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.cache import never_cache

from apps.academics.models import Enrollment, Student, TeachingAssignment
from apps.accounts.decorators import role_required
from apps.accounts.models import Role
from apps.accounts.permissions import requires, visible_assignments
from apps.audit import services as audit
from apps.notifications.services import evaluate_students

from .calculations import student_attendance_summary
from .forms import AttendanceSelectionForm, AttendanceSummaryFilterForm, AttendanceThresholdForm
from .models import AttendanceSession, AttendanceThreshold, Status
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


@never_cache
@role_required(Role.STUDENT)
def attendance_summary(request):
    """Show only the authenticated student's own attendance, with optional filters (BL-15)."""
    student = get_object_or_404(Student, user=request.user)
    form = AttendanceSummaryFilterForm(request.GET or None, student=student)
    summary = None
    if not request.GET:
        summary = student_attendance_summary(student)
    elif form.is_valid():
        data = form.cleaned_data
        summary = student_attendance_summary(
            student,
            subject_id=data["subject"].pk if data["subject"] else None,
            start_date=data["start_date"],
            end_date=data["end_date"],
        )
    threshold = AttendanceThreshold.current_value()
    subject_rows = []
    overall_below = False
    if summary:
        subject_rows = [(row, row.is_below_threshold(threshold)) for row in summary.subjects]
        overall_below = summary.overall.is_below_threshold(threshold)
    return render(
        request,
        "attendance/summary.html",
        {
            "student": student,
            "form": form,
            "summary": summary,
            "subject_rows": subject_rows,
            "overall_below": overall_below,
            "threshold": threshold,
            "filters_applied": bool(request.GET),
        },
    )


@never_cache
@requires("threshold.configure")
def threshold_settings(request):
    """Admin-only institution-wide attendance threshold configuration (BL-22)."""
    current = AttendanceThreshold.current_value()
    form = AttendanceThresholdForm(request.POST or None, initial={"value": current})
    if request.method == "POST" and form.is_valid():
        with transaction.atomic():
            setting, _ = AttendanceThreshold.objects.select_for_update().get_or_create(
                pk=1, defaults={"value": 75}
            )
            previous = setting.value
            setting.value = form.cleaned_data["value"]
            setting.save(update_fields=["value", "updated_at"])
            audit.record(
                "attendance.threshold.update",
                actor=request.user,
                target_type="AttendanceThreshold",
                target_id=setting.pk,
                old_value={"value": previous},
                new_value={"value": setting.value},
            )
            # A threshold change re-evaluates every active student (BL-01 D-14, AR-13).
            evaluate_students(threshold=setting.value)
        messages.success(
            request,
            f"Attendance threshold saved as {setting.value}%. Shortage counts update immediately.",
        )
        return redirect("threshold_settings")
    return render(
        request,
        "attendance/threshold_settings.html",
        {"form": form, "threshold": current},
        status=400 if request.method == "POST" else 200,
    )
