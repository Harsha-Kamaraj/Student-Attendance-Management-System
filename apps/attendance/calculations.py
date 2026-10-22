"""Attendance totals derived from saved records (BL-14; BL-01 D-10 to D-13).

Each record represents one class the student was eligible to attend. Missing
records are not absences: inactive students and students enrolled later must not
be charged for classes that were held without them on the submitted roster.
"""

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
    """Return live shortage counts from persisted records, excluding zero-record cases.

    ``students_below_overall`` counts students whose pooled attendance is below the
    threshold. ``subject_shortages`` counts student/subject pairs below threshold.
    When ``assignments`` is provided, only those classes contribute to either count.
    """
    threshold = AttendanceThreshold.current_value() if threshold is None else threshold
    records = AttendanceRecord.objects.all()
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
    subject_shortages = sum(
        1 for row in subject_groups if row["held"] > 0 and row["attended"] * 100 < threshold * row["held"]
    )

    overall_groups = (
        records.order_by()
        .values("student_id")
        .annotate(
            attended=Count("pk", filter=Q(status=Status.PRESENT)),
            held=Count("pk"),
        )
    )
    students_below_overall = sum(
        1 for row in overall_groups if row["held"] > 0 and row["attended"] * 100 < threshold * row["held"]
    )
    return {
        "threshold": threshold,
        "subject_shortages": subject_shortages,
        "students_below_overall": students_below_overall,
    }
