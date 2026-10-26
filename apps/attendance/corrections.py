"""Authorized, atomic attendance corrections and window configuration (BL-17/18)."""

from datetime import timedelta
from zoneinfo import ZoneInfo

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone

from apps.academics.models import TeachingAssignment
from apps.accounts.models import Role, User
from apps.accounts.permissions import can_correct_attendance
from apps.audit import services as audit

from .models import AttendanceRecord, CorrectionWindow, Status

IST = ZoneInfo("Asia/Kolkata")


def _locked_actor(actor):
    if not getattr(actor, "is_authenticated", False):
        raise PermissionDenied("An active authorized account is required.")
    current = User.objects.select_for_update().filter(pk=actor.pk).first()
    if current is None or not current.is_active:
        raise PermissionDenied("An active authorized account is required.")
    return current


def _reason_text(reason):
    if not isinstance(reason, str):
        raise ValidationError("The reason must be text.")
    return reason.strip()


@transaction.atomic
def correct_attendance(*, actor, record, status, reason=""):
    """Correct one saved mark, logging its exact old/new values in the same transaction.

    Lock order matches submission: actor, assignment, then the existing record.
    The caller's cached role, assignment, date and old status are never trusted.
    """
    actor = _locked_actor(actor)
    assignment_id = (
        AttendanceRecord.objects.filter(pk=record.pk).values_list("session__assignment_id", flat=True).first()
    )
    if assignment_id is None:
        raise ValidationError("This attendance record no longer exists.")
    TeachingAssignment.objects.select_for_update().get(pk=assignment_id)
    try:
        record = (
            AttendanceRecord.objects.select_for_update(of=("self",))
            .select_related("session")
            .get(pk=record.pk)
        )
    except AttendanceRecord.DoesNotExist:
        raise ValidationError("This attendance record no longer exists.") from None
    if record.session.assignment_id != assignment_id:
        raise ValidationError("The attendance assignment changed. Reload the record and try again.")
    if not can_correct_attendance(actor, record):
        raise PermissionDenied("You may correct attendance only in your assigned classes.")
    if status not in Status.values:
        raise ValidationError("Choose Present or Absent.")
    reason = _reason_text(reason)
    override = actor.role == Role.ADMIN
    if override and not reason:
        raise ValidationError("An Admin correction requires a reason.")
    today = timezone.localdate(timezone=IST)
    if record.session.date > today:
        raise ValidationError("Attendance cannot be corrected for a future session.")
    if not override and record.session.date < today - timedelta(days=CorrectionWindow.current_days()):
        raise ValidationError("Correction window closed – contact the Admin.")
    previous = record.status
    if status == previous:
        raise ValidationError("Attendance is already marked with this status. Nothing was changed.")

    record.status = status
    record.save(update_fields=["status"])
    audit.record(
        "attendance.correct",
        actor=actor,
        target_type="AttendanceRecord",
        target_id=record.pk,
        old_value={"status": previous},
        new_value={"status": status},
        reason=reason,
        is_admin_override=override,
    )
    return record


@transaction.atomic
def update_correction_window(*, actor, days, reason):
    """Persist one Admin-approved 0–30 day setting, with its reason and audit trail."""
    actor = _locked_actor(actor)
    if actor.role != Role.ADMIN:
        raise PermissionDenied("Only the Admin may configure the correction window.")
    if type(days) is not int or not 0 <= days <= 30:
        raise ValidationError("The correction window must be a whole number from 0 to 30 days.")
    reason = _reason_text(reason)
    if not reason:
        raise ValidationError("A reason is required to change the correction window.")
    setting, _ = CorrectionWindow.objects.select_for_update().get_or_create(pk=1)
    previous = setting.days
    if previous == days:
        raise ValidationError("The correction window already has this value. Nothing was changed.")
    setting.days = days
    setting.save(update_fields=["days", "updated_at"])
    audit.record(
        "correction_window.update",
        actor=actor,
        target_type="CorrectionWindow",
        target_id=setting.pk,
        old_value={"days": previous},
        new_value={"days": days},
        reason=reason,
    )
    return setting
