"""Attendance totals derived from saved records (BL-14; BL-01 D-10 to D-13).

Each record represents one class the student was eligible to attend. Missing
records are not absences: inactive students and students enrolled later must not
be charged for classes that were held without them on the submitted roster.
"""

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

from django.db.models import Count, Q

from apps.academics.models import Enrollment, Subject

from .models import AttendanceRecord, Status


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

    def is_below_threshold(self, threshold: int = 75) -> bool:
        """Compare the exact ratio, rather than its rounded display (D-13)."""
        return self.held > 0 and self.attended * 100 < threshold * self.held


@dataclass(frozen=True)
class SubjectAttendance(AttendanceTotals):
    subject: Subject


@dataclass(frozen=True)
class StudentAttendanceSummary:
    subjects: list[SubjectAttendance]
    overall: AttendanceTotals


def student_attendance_summary(student, *, assignments=None) -> StudentAttendanceSummary:
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

    counts = {
        row["session__assignment__subject_id"]: (row["attended"], row["held"])
        for row in records.order_by()
        .values("session__assignment__subject_id")
        .annotate(attended=Count("pk", filter=Q(status=Status.PRESENT)), held=Count("pk"))
    }
    subjects = Subject.objects.filter(Q(pk__in=enrollments.values("subject_id")) | Q(pk__in=counts)).order_by(
        "code", "pk"
    )
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
