"""Attendance sessions and per-student records."""

from django.conf import settings
from django.db import models

from apps.academics.models import Student, TeachingAssignment

MAX_PERIODS_PER_DAY = 6


class AttendanceSession(models.Model):
    """One class meeting, identified by section + subject + date + period (BL-01 D-08).

    The teaching assignment is unique per section and subject, so the
    unique (assignment, date, period) constraint enforces the session key.
    """

    assignment = models.ForeignKey(TeachingAssignment, on_delete=models.PROTECT, related_name="sessions")
    date = models.DateField()
    period = models.PositiveSmallIntegerField()
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    recorded_by_code = models.CharField(
        max_length=20, blank=True, help_text="Faculty ID kept even if the faculty account is deleted."
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["assignment", "date", "period"], name="session_unique_key"),
            models.CheckConstraint(
                condition=models.Q(period__gte=1, period__lte=MAX_PERIODS_PER_DAY),
                name="session_period_range",
            ),
        ]

    def __str__(self):
        return f"{self.assignment} on {self.date} period {self.period}"


class Status(models.TextChoices):
    """Only Present and Absent are permitted (BL-01 D-06)."""

    PRESENT = "P", "Present"
    ABSENT = "A", "Absent"


class AttendanceRecord(models.Model):
    Status = Status

    session = models.ForeignKey(AttendanceSession, on_delete=models.PROTECT, related_name="records")
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name="attendance_records")
    status = models.CharField(max_length=1, choices=Status.choices)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["session", "student"], name="record_one_per_student_session"),
            models.CheckConstraint(condition=models.Q(status__in=Status.values), name="record_status_valid"),
        ]

    def __str__(self):
        return f"{self.student} {self.get_status_display()} – {self.session}"
