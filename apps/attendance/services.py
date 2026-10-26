"""Atomic attendance creation shared by the HTML workflow and future APIs."""

from collections.abc import Mapping
from datetime import date, timedelta
from zoneinfo import ZoneInfo

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone

from apps.academics.models import Enrollment, Faculty, TeachingAssignment
from apps.accounts.models import Role, User
from apps.accounts.permissions import can_mark_attendance
from apps.audit import services as audit

from .models import MAX_PERIODS_PER_DAY, AttendanceRecord, AttendanceSession, CorrectionWindow, Status

OUTSIDE_WINDOW_MESSAGE = (
    "This date is outside the configured correction window. "
    "Contact the Admin, who can record the session with a reason."
)


def earliest_faculty_date():
    """Oldest session date a faculty member may still record (AR-06, AR-08)."""
    return timezone.localdate(timezone=ZoneInfo("Asia/Kolkata")) - timedelta(
        days=CorrectionWindow.current_days()
    )


@transaction.atomic
def submit_attendance(*, actor, assignment, day, period, statuses, reason=""):
    """Create complete sessions, serialize concurrent writers, and safely retry identical submissions.

    ``statuses`` maps student IDs to P/A. Failed writes roll back the whole session.
    Locking the TeachingAssignment prevents two submissions for the same subject/section
    from checking an empty session simultaneously. Database uniqueness is a backup guard.
    """
    if not getattr(actor, "is_authenticated", False):
        raise PermissionDenied("An active faculty or Admin account is required.")
    actor = User.objects.select_for_update().filter(pk=actor.pk).first()
    if actor is None:
        raise PermissionDenied("An active faculty or Admin account is required.")
    assignment = TeachingAssignment.objects.select_for_update().get(pk=assignment.pk)
    if not can_mark_attendance(actor, assignment):
        raise PermissionDenied("Class is outside your teaching assignments.")
    if type(day) is not date:
        raise ValidationError("Choose a valid attendance date.")
    if day > timezone.localdate():
        raise ValidationError("Attendance cannot be recorded for a future date.")
    if type(period) is not int or not 1 <= period <= MAX_PERIODS_PER_DAY:
        raise ValidationError("Invalid class period.")
    if (
        not isinstance(statuses, Mapping)
        or any(type(sid) is not int or sid <= 0 for sid in statuses)
        or any(value not in (Status.PRESENT, Status.ABSENT) for value in statuses.values())
    ):
        raise ValidationError("Submit one Present or Absent status for each student using valid student IDs.")
    if not isinstance(reason, str):
        raise ValidationError("The attendance reason must be text.")
    if actor.role == Role.ADMIN and not reason.strip():
        raise ValidationError("Admin attendance overrides require a reason.")

    # Check for an earlier submission while holding the per-assignment row lock.
    # Historical rosters may differ from today's, so an identical retry compares
    # with the *saved* session, not with today's active enrollment list.
    existing = AttendanceSession.objects.filter(assignment=assignment, date=day, period=period).first()
    if existing:
        saved = dict(existing.records.values_list("student_id", "status"))
        if saved and saved == statuses:
            return existing, False
        raise ValidationError(
            "Attendance is already recorded for this class, date and period with different values. "
            "Use the correction workflow; changes cannot overwrite a saved session."
        )

    if actor.role == Role.FACULTY and day < earliest_faculty_date():
        raise ValidationError(OUTSIDE_WINDOW_MESSAGE)

    student_ids = list(
        Enrollment.objects.filter(assignment=assignment, student__user__is_active=True)
        .order_by("student_id")
        .values_list("student_id", flat=True)
    )
    if not student_ids:
        raise ValidationError("No active enrolled students exist for this class.")
    if set(statuses) != set(student_ids) or any(
        value not in (Status.PRESENT, Status.ABSENT) for value in statuses.values()
    ):
        raise ValidationError("Mark every enrolled student as Present or Absent before saving.")
    faculty_code = ""
    if actor.role == Role.FACULTY:
        faculty_code = Faculty.objects.filter(user=actor).values_list("faculty_id", flat=True).first() or ""
    session = AttendanceSession.objects.create(
        assignment=assignment,
        date=day,
        period=period,
        recorded_by=actor,
        recorded_by_code=faculty_code,
    )
    AttendanceRecord.objects.bulk_create(
        [AttendanceRecord(session=session, student_id=sid, status=statuses[sid]) for sid in student_ids]
    )
    audit.record(
        "attendance.mark",
        actor=actor,
        target_type="AttendanceSession",
        target_id=session.pk,
        new_value={"assignment_id": assignment.pk, "date": day.isoformat(), "period": period},
        reason=reason.strip(),
        is_admin_override=actor.role == Role.ADMIN,
    )
    return session, True
