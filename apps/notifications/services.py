"""Low-attendance detection, student notifications and the faculty shortage list (UC-10).

Rules (BL-01 D-11, D-13 to D-15, D-03):
- A percentage is below the threshold when ``attended * 100 < threshold * held``. Equal is
  not below; a subject (or student) with no recorded classes is never flagged.
- Subject percentages and the pooled overall percentage are evaluated separately.
- A student is notified (one in-app notification and one email) only when a percentage
  moves from not below to below. No repeats while it stays below; recovery clears the flag.
- A threshold change re-evaluates every active student.
- If email fails, the in-app notification is still delivered and the failure is logged.
- Deactivated students are not evaluated and receive nothing.
- Faculty see only their assigned subjects; every Monday at 08:00 IST each faculty member
  with a non-empty list receives one email.
"""

import logging
from collections import defaultdict
from dataclasses import dataclass
from datetime import timedelta
from functools import partial
from zoneinfo import ZoneInfo

from django.conf import settings
from django.core.mail import send_mail
from django.db import IntegrityError, transaction
from django.db.models import Count, Q
from django.urls import reverse
from django.utils import timezone

from apps.academics.models import Enrollment, Faculty, Student, Subject, TeachingAssignment
from apps.accounts.models import Role
from apps.accounts.permissions import visible_assignments
from apps.attendance.calculations import AttendanceTotals
from apps.attendance.models import AttendanceRecord, AttendanceThreshold, Status
from apps.audit import services as audit

from .models import Notification, ShortageFlag, WeeklyShortageEmail

logger = logging.getLogger(__name__)

IST = ZoneInfo("Asia/Kolkata")


def is_below(attended, held, threshold):
    """Exact comparison with the threshold (D-13); zero classes are never below (D-11)."""
    return held > 0 and attended * 100 < threshold * held


def _grouped_counts(records, *keys):
    return (
        records.order_by()
        .values(*keys)
        .annotate(attended=Count("pk", filter=Q(status=Status.PRESENT)), held=Count("pk"))
    )


# --- Student evaluation and notification (BL-23) ------------------------------------------


def students_below(student_ids, threshold):
    """Return ``{student_id: {subject_id or None: AttendanceTotals}}`` for percentages below threshold.

    ``None`` is the pooled overall percentage across all of the student's records (D-10).
    """
    result = defaultdict(dict)
    overall = defaultdict(lambda: [0, 0])
    records = AttendanceRecord.objects.filter(student_id__in=student_ids)
    for row in _grouped_counts(records, "student_id", "session__assignment__subject_id"):
        student_id, subject_id = row["student_id"], row["session__assignment__subject_id"]
        overall[student_id][0] += row["attended"]
        overall[student_id][1] += row["held"]
        if is_below(row["attended"], row["held"], threshold):
            result[student_id][subject_id] = AttendanceTotals(attended=row["attended"], held=row["held"])
    for student_id, (attended, held) in overall.items():
        if is_below(attended, held, threshold):
            result[student_id][None] = AttendanceTotals(attended=attended, held=held)
    return result


def _student_message(items, threshold):
    lines = [f"Your attendance is below the required {threshold}% in:"]
    for subject, totals in items:
        label = str(subject) if subject else "Overall attendance"
        lines.append(f"- {label}: {totals.display}")
    lines += [
        "",
        f"Attend upcoming classes to bring it back to {threshold}% or above. "
        "If a mark looks wrong, contact your faculty member or the Admin.",
    ]
    return "\n".join(lines)


def evaluate_students(student_ids=None, *, threshold=None):
    """Sync shortage flags for active students and notify each new drop (UC-10 steps 1-4).

    ``student_ids=None`` re-evaluates every active student (threshold change, AR-13).
    Call this inside the transaction that saved the attendance or threshold, so flags and
    in-app notifications commit with the change that caused them. Emails go out only after
    the commit, so a rolled-back save never emails anyone. Returns the new notifications.
    """
    if threshold is None:
        threshold = AttendanceThreshold.current_value()
    students = Student.objects.filter(user__is_active=True)
    if student_ids is not None:
        students = students.filter(pk__in=list(student_ids))
    # Locking the students (in key order, to avoid deadlocks) makes concurrent saves for the
    # same student evaluate one after the other, so a single drop cannot notify twice.
    locked = {
        student.pk: student
        for student in students.select_for_update(of=("self",)).select_related("user").order_by("pk")
    }
    if not locked:
        return []

    below = students_below(locked.keys(), threshold)
    current = {(sid, subject_id) for sid, subjects in below.items() for subject_id in subjects}
    existing = set(ShortageFlag.objects.filter(student_id__in=locked).values_list("student_id", "subject_id"))

    recovered = existing - current
    if recovered:
        condition = Q()
        for sid, subject_id in recovered:
            condition |= Q(student_id=sid, subject_id=subject_id)
        ShortageFlag.objects.filter(condition).delete()

    new = sorted(current - existing, key=lambda pair: (pair[0], pair[1] is None, pair[1] or 0))
    if not new:
        return []
    ShortageFlag.objects.bulk_create([ShortageFlag(student_id=sid, subject_id=sub) for sid, sub in new])

    subjects = Subject.objects.in_bulk({sub for _, sub in new if sub is not None})
    by_student = defaultdict(list)
    for sid, subject_id in new:
        by_student[sid].append((subjects.get(subject_id), below[sid][subject_id]))

    notifications = []
    for sid, items in by_student.items():
        items.sort(key=lambda item: (item[0] is None, item[0].code if item[0] else ""))
        notification = Notification(
            recipient=locked[sid].user,  # only the affected student (SEC-25)
            title=f"Low attendance: below {threshold}%",
            body=_student_message(items, threshold),
        )
        notifications.append(notification)
    Notification.objects.bulk_create(notifications)
    # A class can cross the threshold for 60 students at once. Insert the batch
    # together and reload recipients once after commit, rather than once per
    # student. Each recipient still receives a separate, private email.
    transaction.on_commit(partial(send_notification_emails, tuple(note.pk for note in notifications)))
    return notifications


def _log_email_failure(action, *, target_type, target_id, error):
    logger.warning("%s for %s %s: %s", action, target_type, target_id, error)
    audit.record(action, target_type=target_type, target_id=target_id, new_value={"error": error})


def send_notification_email(notification_id):
    """Email one in-app notification to its recipient. Failures are logged, never raised (AR-13)."""
    return bool(send_notification_emails([notification_id]))


def send_notification_emails(notification_ids):
    """Read committed recipients in one query; isolate delivery failure per recipient."""
    notifications = Notification.objects.select_related("recipient").filter(pk__in=notification_ids)
    return sum(_send_notification_email(notification) for notification in notifications)


def _send_notification_email(notification):
    address = notification.recipient.email
    if not address:
        _log_email_failure(
            "notification.email_failed",
            target_type="Notification",
            target_id=notification.pk,
            error="No email address on the account.",
        )
        return False
    try:
        send_mail(notification.title, notification.body, settings.DEFAULT_FROM_EMAIL, [address])
    except Exception as exc:  # any provider failure must not affect the in-app notification
        _log_email_failure(
            "notification.email_failed",
            target_type="Notification",
            target_id=notification.pk,
            error=f"{exc.__class__.__name__}: {exc}",
        )
        return False
    return True


# --- Below-threshold list (BL-24) -----------------------------------------------------------


@dataclass(frozen=True)
class ShortageRow(AttendanceTotals):
    student: Student
    subject: Subject | None
    section: str = ""


def subject_shortage_rows(assignments, threshold=None):
    """Active students below threshold per subject, counting only classes in ``assignments``."""
    threshold = AttendanceThreshold.current_value() if threshold is None else threshold
    records = AttendanceRecord.objects.filter(
        session__assignment__in=assignments, student__user__is_active=True
    )
    groups = [
        row
        for row in _grouped_counts(records, "student_id", "session__assignment__subject_id")
        if is_below(row["attended"], row["held"], threshold)
    ]
    if not groups:
        return []
    student_ids = {row["student_id"] for row in groups}
    subject_ids = {row["session__assignment__subject_id"] for row in groups}
    students = Student.objects.in_bulk(student_ids)
    subjects = Subject.objects.in_bulk(subject_ids)
    sections = {
        (e.student_id, e.subject_id): str(e.assignment.section)
        for e in Enrollment.objects.filter(
            student_id__in=student_ids, subject_id__in=subject_ids
        ).select_related("assignment__section")
    }
    rows = [
        ShortageRow(
            attended=row["attended"],
            held=row["held"],
            student=students[row["student_id"]],
            subject=subjects[row["session__assignment__subject_id"]],
            section=sections.get((row["student_id"], row["session__assignment__subject_id"]), ""),
        )
        for row in groups
    ]
    return sorted(rows, key=lambda r: (r.subject.code, r.student.roll_number))


def overall_shortage_rows(threshold=None):
    """Active students whose pooled overall percentage is below threshold (Admin scope)."""
    threshold = AttendanceThreshold.current_value() if threshold is None else threshold
    records = AttendanceRecord.objects.filter(student__user__is_active=True)
    groups = [
        row
        for row in _grouped_counts(records, "student_id")
        if is_below(row["attended"], row["held"], threshold)
    ]
    students = Student.objects.select_related("home_section").in_bulk({row["student_id"] for row in groups})
    rows = [
        ShortageRow(
            attended=row["attended"],
            held=row["held"],
            student=students[row["student_id"]],
            subject=None,
            section=str(students[row["student_id"]].home_section or ""),
        )
        for row in groups
    ]
    return sorted(rows, key=lambda r: r.student.roll_number)


def shortage_list_for(user, threshold=None):
    """The current list for one viewer: ``(overall_rows, subject_rows)``.

    Faculty see only their assigned subjects; an overall percentage would include other
    faculty members' classes, so overall rows are shown to the Admin only (D-15, SEC-25).
    """
    threshold = AttendanceThreshold.current_value() if threshold is None else threshold
    subject_rows = subject_shortage_rows(visible_assignments(user), threshold)
    overall_rows = overall_shortage_rows(threshold) if user.role == Role.ADMIN else []
    return overall_rows, subject_rows


# --- Monday faculty email (BL-24, D-15) ---------------------------------------------------


def week_start(now=None):
    today = timezone.localdate(now or timezone.now(), timezone=IST)
    return today - timedelta(days=today.weekday())


def _faculty_message(faculty, rows, threshold, monday):
    lines = [
        f"Dear {faculty.full_name},",
        "",
        f"These students in your subjects are below the {threshold}% attendance threshold "
        f"(week of {monday:%d %b %Y}):",
    ]
    current_subject = None
    for row in rows:
        if row.subject != current_subject:
            current_subject = row.subject
            lines += ["", str(row.subject)]
        section = f" ({row.section})" if row.section else ""
        lines.append(f"- {row.student.roll_number} {row.student.full_name}{section}: {row.display}")
    lines += ["", f"The current list is always available at {reverse('shortage_list')}."]
    return "\n".join(lines)


def send_weekly_faculty_emails(*, now=None):
    """Send each active faculty member one email listing their students below threshold.

    No email is sent when the list is empty, and at most one per faculty member per week:
    re-running the job in the same week skips faculty already emailed. A failed send is
    logged and can be retried by running the job again.
    """
    threshold = AttendanceThreshold.current_value()
    monday = week_start(now)
    result = {"sent": 0, "empty": 0, "already_sent": 0, "failed": 0}
    faculty_members = (
        Faculty.objects.filter(user__is_active=True, assignments__isnull=False)
        .distinct()
        .select_related("user")
        .order_by("faculty_id")
    )
    for faculty in faculty_members:
        rows = subject_shortage_rows(TeachingAssignment.objects.filter(faculty=faculty), threshold)
        if not rows:
            result["empty"] += 1
            continue
        try:
            with transaction.atomic():
                sent = WeeklyShortageEmail.objects.create(
                    faculty=faculty,
                    week_start=monday,
                    student_count=len({row.student.pk for row in rows}),
                )
        except IntegrityError:
            result["already_sent"] += 1
            continue

        error = None
        if not faculty.user.email:
            error = "No email address on the account."
        else:
            try:
                send_mail(
                    f"Weekly low-attendance list: {sent.student_count} student(s) below {threshold}%",
                    _faculty_message(faculty, rows, threshold, monday),
                    settings.DEFAULT_FROM_EMAIL,
                    [faculty.user.email],  # only this faculty member's own students (SEC-25)
                )
            except Exception as exc:  # log and allow a retry on the next run
                error = f"{exc.__class__.__name__}: {exc}"
        if error:
            sent.delete()
            _log_email_failure(
                "notification.weekly_email_failed",
                target_type="Faculty",
                target_id=faculty.faculty_id,
                error=error,
            )
            result["failed"] += 1
            continue
        audit.record(
            "notification.weekly_email_sent",
            target_type="Faculty",
            target_id=faculty.faculty_id,
            new_value={"week_start": monday.isoformat(), "students": sent.student_count},
        )
        result["sent"] += 1
    return result
