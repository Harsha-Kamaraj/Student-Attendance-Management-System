"""Attendance totals derived from saved records (BL-14; BL-01 D-10 to D-13).

Each record represents one class the student was eligible to attend. Missing
records are not absences: inactive students and students enrolled later must not
be charged for classes that were held without them on the submitted roster.
"""

from collections import defaultdict
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

from django.db.models import Count, Q

from apps.academics.models import Enrollment, Subject

from .models import AttendanceRecord, AttendanceThreshold, Status


@dataclass(frozen=True)
class AttendanceTotals:
    attended: int
    held: int

    @property
    def percentage(self) -> Decimal | None:
        if not self.held:
            return None
        return (Decimal(self.attended) * 100 / Decimal(self.held)).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )

    @property
    def display(self) -> str:
        percentage = self.percentage
        if percentage is None:
            return "N/A – no classes yet"
        return f"{self.attended}/{self.held} ({percentage:.2f}%)"

    def is_below_threshold(self, threshold: int | None = None) -> bool:
        """Compare the exact ratio using the current institution threshold (D-13)."""
        if threshold is None:
            threshold = AttendanceThreshold.current_value()
        return self.held > 0 and self.attended * 100 < threshold * self.held


@dataclass(frozen=True)
class SubjectAttendance(AttendanceTotals):
    subject: Subject


@dataclass(frozen=True)
class StudentAttendanceSummary:
    subjects: list[SubjectAttendance]
    overall: AttendanceTotals


def student_attendance_summary(
    student, *, assignments=None, subject_id=None, start_date=None, end_date=None
) -> StudentAttendanceSummary:
    """Return current subject and pooled totals, optionally within assigned classes.

    The caller supplies authorized assignments for a faculty-scoped view. Omitting
    the scope returns the student's complete history, including subjects whose
    enrollment has since been removed. Two queries serve any number of subjects;
    percentages are calculated from counts on every call, so saved corrections
    are immediately reflected without cache invalidation or stored percentages.
    """
    records = AttendanceRecord.objects.filter(student=student)
    enrollments = Enrollment.objects.filter(student=student)
    if assignments is not None:
        records = records.filter(session__assignment__in=assignments)
        enrollments = enrollments.filter(assignment__in=assignments)
    if subject_id is not None:
        records = records.filter(session__assignment__subject_id=subject_id)
        enrollments = enrollments.filter(subject_id=subject_id)
    if start_date is not None:
        records = records.filter(session__date__gte=start_date)
    if end_date is not None:
        records = records.filter(session__date__lte=end_date)

    counts = {
        row["session__assignment__subject_id"]: (row["attended"], row["held"])
        for row in records.order_by()
        .values("session__assignment__subject_id")
        .annotate(attended=Count("pk", filter=Q(status=Status.PRESENT)), held=Count("pk"))
    }
    subjects_query = Q(pk__in=counts)
    # Date-filtered reports show only subjects with records in the selected period.
    # Without a date filter, enrolled subjects with no records remain visible as N/A.
    if start_date is None and end_date is None:
        subjects_query |= Q(pk__in=enrollments.values("subject_id"))
    subjects = Subject.objects.filter(subjects_query).order_by("code", "pk")
    rows = [
        SubjectAttendance(
            subject=subject,
            attended=counts.get(subject.pk, (0, 0))[0],
            held=counts.get(subject.pk, (0, 0))[1],
        )
        for subject in subjects
    ]
    return StudentAttendanceSummary(
        subjects=rows,
        overall=AttendanceTotals(
            attended=sum(row.attended for row in rows),
            held=sum(row.held for row in rows),
        ),
    )


def attendance_shortage_statistics(*, assignments=None, threshold=None):
    """Return live shortage counts for active students, excluding zero-record cases.

    ``students_below_overall`` counts students whose pooled attendance is below the
    threshold. ``subject_shortages`` counts student/subject pairs below threshold.
    When ``assignments`` is provided, only those classes contribute to either count.
    """
    threshold = AttendanceThreshold.current_value() if threshold is None else threshold
    # Deactivated students are not evaluated (BL-01 D-03), matching the below-threshold
    # list and the alerts, so a dashboard count always equals the list it links to.
    records = AttendanceRecord.objects.filter(student__user__is_active=True)
    if assignments is not None:
        records = records.filter(session__assignment__in=assignments)

    subject_groups = (
        records.order_by()
        .values("student_id", "session__assignment__subject_id")
        .annotate(
            attended=Count("pk", filter=Q(status=Status.PRESENT)),
            held=Count("pk"),
        )
    )
    # Pool the same scoped subject counts instead of scanning all attendance a
    # second time. Both dashboard metrics now describe one database snapshot.
    overall = defaultdict(lambda: [0, 0])
    subject_shortages = 0
    for row in subject_groups:
        attended, held = row["attended"], row["held"]
        overall[row["student_id"]][0] += attended
        overall[row["student_id"]][1] += held
        subject_shortages += held > 0 and attended * 100 < threshold * held
    students_below_overall = sum(
        1 for attended, held in overall.values() if held > 0 and attended * 100 < threshold * held
    )
    return {
        "threshold": threshold,
        "subject_shortages": subject_shortages,
        "students_below_overall": students_below_overall,
    }


# --- How many classes a student still needs (student dashboard, My attendance, alerts) -------


def _ceil_div(numerator, denominator):
    return -(-numerator // denominator)


def classes_needed(attended, held, threshold):
    """Classes the student must attend in a row to bring ``attended/held`` up to the threshold.

    ``(attended + x) / (held + x) >= threshold / 100``  gives
    ``x >= (threshold * held - 100 * attended) / (100 - threshold)``.
    Returns 0 when already at or above the threshold, and ``None`` when the threshold is
    100% and a class has been missed (no number of classes can restore it).
    """
    if held == 0 or attended * 100 >= threshold * held:
        return 0
    if threshold >= 100:
        return None
    return _ceil_div(threshold * held - 100 * attended, 100 - threshold)


def classes_can_miss(attended, held, threshold):
    """Classes the student could miss in a row and still stay at or above the threshold."""
    if held == 0 or threshold <= 0 or attended * 100 < threshold * held:
        return 0
    return (100 * attended - threshold * held) // threshold


def _plural(count, word="class"):
    return f"{count} {word}{'' if count == 1 else 'es'}"


@dataclass(frozen=True)
class AttendanceOutlook:
    """Plain-language guidance for one subject (or overall) at the current threshold."""

    attended: int
    held: int
    threshold: int
    planned: int | None = None

    @property
    def below(self):
        return self.held > 0 and self.attended * 100 < self.threshold * self.held

    @property
    def display(self):
        return AttendanceTotals(self.attended, self.held).display

    @property
    def needed(self):
        return classes_needed(self.attended, self.held, self.threshold)

    @property
    def can_miss(self):
        return classes_can_miss(self.attended, self.held, self.threshold)

    @property
    def remaining(self):
        """Classes still to be held this semester, when the Admin has set a semester total."""
        if self.planned is None:
            return None
        return max(self.planned - self.held, 0)

    @property
    def must_attend(self):
        """Of the remaining classes, how many must be attended to end the semester at the threshold."""
        if self.planned is None:
            return None
        return max(_ceil_div(self.threshold * max(self.planned, self.held), 100) - self.attended, 0)

    @property
    def message(self):
        if self.held == 0:
            return "No classes held yet."
        if self.planned is not None:
            remaining, must = self.remaining, self.must_attend
            if must > remaining:
                best = (
                    Decimal(self.attended + remaining) * 100 / Decimal(max(self.planned, self.held))
                ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
                return (
                    f"Even attending all {_plural(remaining)} left this semester gives {best}%, "
                    f"below {self.threshold}%. Speak to your faculty member."
                )
            if must == 0:
                return f"You have already secured {self.threshold}% for this semester."
            return (
                f"Attend at least {must} of the {_plural(remaining)} left this semester "
                f"to finish at {self.threshold}% or above."
            )
        if self.below:
            if self.needed is None:
                return f"A {self.threshold}% threshold cannot be reached after a missed class."
            return f"Attend the next {_plural(self.needed)} to get back to {self.threshold}%."
        if self.can_miss:
            return f"You can miss {_plural(self.can_miss)} and still stay at {self.threshold}% or above."
        return f"Attend your next class to stay at {self.threshold}% or above."


def planned_sessions_by_subject(student):
    """``{subject_id: planned total}`` for the student's enrolled classes that have a semester total."""
    return {
        subject_id: planned
        for subject_id, planned in Enrollment.objects.filter(
            student=student, assignment__planned_sessions__isnull=False
        ).values_list("subject_id", "assignment__planned_sessions")
    }


def subject_outlooks(student, summary, threshold):
    """Pair each subject row in ``summary`` with its outlook, plus the overall outlook.

    The overall outlook uses a semester total only when every listed subject has one.
    """
    planned = planned_sessions_by_subject(student)
    rows = [
        (row, AttendanceOutlook(row.attended, row.held, threshold, planned.get(row.subject.pk)))
        for row in summary.subjects
    ]
    overall_planned = None
    if rows and all(row.subject.pk in planned for row, _ in rows):
        overall_planned = sum(planned[row.subject.pk] for row, _ in rows)
    overall = AttendanceOutlook(summary.overall.attended, summary.overall.held, threshold, overall_planned)
    return rows, overall
