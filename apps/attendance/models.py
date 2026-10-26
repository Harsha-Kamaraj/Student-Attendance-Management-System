"""Attendance sessions and per-student records."""

from django.conf import settings
from django.db import models

from apps.academics.models import Student, TeachingAssignment

MAX_PERIODS_PER_DAY = 6

# Default only: the Admin-configured value is persisted by CorrectionWindow.
CORRECTION_WINDOW_DAYS = 2


class AttendanceSession(models.Model):
    """One class meeting, identified by section + subject + date + period (BL-01 D-08).

    The teaching assignment is unique per section and subject, so the
    unique (assignment, date, period) constraint enforces the session key.
    """

    assignment = models.ForeignKey(
        TeachingAssignment,
        on_delete=models.PROTECT,
        related_name="sessions",
    )
    date = models.DateField()
    period = models.PositiveSmallIntegerField()
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    recorded_by_code = models.CharField(
        max_length=20,
        blank=True,
        help_text="Faculty ID kept even if the faculty account is deleted.",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["assignment", "date", "period"],
                name="session_unique_key",
            ),
            models.CheckConstraint(
                condition=models.Q(
                    period__gte=1,
                    period__lte=MAX_PERIODS_PER_DAY,
                ),
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

    session = models.ForeignKey(
        AttendanceSession,
        on_delete=models.PROTECT,
        related_name="records",
    )
    student = models.ForeignKey(
        Student,
        on_delete=models.CASCADE,
        related_name="attendance_records",
    )
    status = models.CharField(max_length=1, choices=Status.choices)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["session", "student"],
                name="record_one_per_student_session",
            ),
            models.CheckConstraint(
                condition=models.Q(status__in=Status.values),
                name="record_status_valid",
            ),
        ]

    def __str__(self):
        return f"{self.student} {self.get_status_display()} - {self.session}"


class AttendanceThreshold(models.Model):
    value = models.PositiveSmallIntegerField(default=75)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(value__gte=1, value__lte=100),
                name="attendance_threshold_range",
            ),
        ]

    def __str__(self):
        return f"Attendance threshold: {self.value}%"

    @classmethod
    def current_value(cls):
        row = cls.objects.first()
        return row.value if row else 75


class CorrectionWindow(models.Model):
    """One institution-wide faculty correction/missed-session window (BL-17)."""

    id = models.PositiveSmallIntegerField(primary_key=True, default=1, editable=False)
    days = models.PositiveSmallIntegerField(default=CORRECTION_WINDOW_DAYS)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.CheckConstraint(condition=models.Q(pk=1), name="correction_window_singleton"),
            models.CheckConstraint(
                condition=models.Q(days__gte=0, days__lte=30), name="correction_window_days_range"
            ),
        ]

    def __str__(self):
        return f"Faculty correction window: {self.days} days"

    @classmethod
    def current_days(cls):
        days = cls.objects.filter(pk=1).values_list("days", flat=True).first()
        return CORRECTION_WINDOW_DAYS if days is None else days
