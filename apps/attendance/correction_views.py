"""Correct an authorized record and configure the calendar-day window (BL-17)."""

import logging
from datetime import timedelta

from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db import DatabaseError
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods

from apps.accounts.decorators import role_required
from apps.accounts.models import Role
from apps.accounts.permissions import get_visible_or_deny, requires, visible_attendance_records

from .correction_forms import AttendanceCorrectionForm, CorrectionWindowForm
from .corrections import IST, correct_attendance, update_correction_window
from .models import AttendanceRecord, CorrectionWindow

logger = logging.getLogger(__name__)


@never_cache
@requires("attendance.correct")
@require_http_methods(["GET", "POST"])
def attendance_correct(request, pk):
    record = get_visible_or_deny(
        visible_attendance_records(request.user).select_related(
            "student__user", "session__assignment__subject", "session__assignment__section"
        ),
        AttendanceRecord,
        pk,
    )
    form = AttendanceCorrectionForm(
        request.POST if request.method == "POST" else None,
        user=request.user,
        initial={"status": record.status},
    )
    if request.method == "POST" and form.is_valid():
        try:
            correct_attendance(
                actor=request.user,
                record=record,
                status=form.cleaned_data["status"],
                reason=form.cleaned_data["reason"],
            )
        except ValidationError as error:
            form.add_error(None, " ".join(error.messages))
        except DatabaseError:
            logger.exception("Attendance correction failed")
            form.add_error(
                None, "The correction could not be saved. No changes were saved. Please try again."
            )
        else:
            messages.success(request, "Attendance corrected. The change has been recorded in the history.")
            return redirect("attendance_changes", pk=record.pk)
    days = CorrectionWindow.current_days()
    deadline = record.session.date + timedelta(days=days)
    today = timezone.localdate(timezone=IST)
    can_edit = request.user.role == Role.ADMIN or record.session.date <= today <= deadline
    return render(
        request,
        "attendance/correct.html",
        {"record": record, "form": form, "days": days, "deadline": deadline, "can_edit": can_edit},
    )


@never_cache
@role_required(Role.ADMIN)
@require_http_methods(["GET", "POST"])
def correction_window_settings(request):
    form = CorrectionWindowForm(
        request.POST if request.method == "POST" else None, initial={"days": CorrectionWindow.current_days()}
    )
    if request.method == "POST" and form.is_valid():
        try:
            update_correction_window(
                actor=request.user, days=form.cleaned_data["days"], reason=form.cleaned_data["reason"]
            )
        except ValidationError as error:
            form.add_error(None, " ".join(error.messages))
        except DatabaseError:
            logger.exception("Correction-window policy update failed")
            form.add_error(None, "The correction window could not be saved. No changes were saved.")
        else:
            messages.success(request, "Faculty correction window updated.")
            return redirect("correction_window_settings")
    return render(request, "attendance/correction_window.html", {"form": form})
