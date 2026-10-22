"""Atomic attendance creation shared by the HTML workflow and future APIs."""

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone

from apps.academics.models import Enrollment, Faculty
from apps.accounts.models import Role
from apps.accounts.permissions import can_mark_attendance
from apps.audit import services as audit

from .models import MAX_PERIODS_PER_DAY, AttendanceRecord, AttendanceSession, Status


@transaction.atomic
def submit_attendance(*, actor, assignment, day, period, statuses, reason=""):
    """Create a *complete* class session; any failure rolls everything back.

    ``statuses`` maps student IDs to P/A. Partial or extra rosters never save.
    BL-13 adds explicit retry idempotency and concurrent-request serialization.
    """
    if not can_mark_attendance(actor, assignment):
        raise PermissionDenied("Class is outside your teaching assignments.")
    if day > timezone.localdate():
        raise ValidationError("Attendance cannot be recorded for a future date.")
    if not 1 <= period <= MAX_PERIODS_PER_DAY:
        raise ValidationError("Invalid class period.")
    if actor.role == Role.ADMIN and not reason.strip():
        raise ValidationError("Admin attendance overrides require a reason.")

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
    if AttendanceSession.objects.filter(assignment=assignment, date=day, period=period).exists():
        raise ValidationError("Attendance is already recorded for this class, date and period.")

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
