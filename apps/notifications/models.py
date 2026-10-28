"""Low-attendance notifications (BL-23) and weekly faculty shortage emails (BL-24).

BL-01 D-14: a student is notified once each time a subject or overall percentage moves
from not below to below the threshold. ``ShortageFlag`` remembers what is currently below,
so repeated saves while still below send nothing, and recovery deletes the flag so a later
drop notifies again.
"""

from django.conf import settings
from django.db import models

from apps.academics.models import Faculty, Student, Subject


class Notification(models.Model):
    """One in-app message, visible only to its recipient."""

    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications"
    )
    title = models.CharField(max_length=200)
    body = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at", "-pk"]

    def __str__(self):
        return f"{self.title} → {self.recipient}"


class ShortageFlag(models.Model):
    """The student is currently below the threshold for ``subject`` (``None`` = overall)."""

    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name="shortage_flags")
    subject = models.ForeignKey(
        Subject, on_delete=models.CASCADE, null=True, blank=True, related_name="shortage_flags"
    )
    flagged_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            # NULLS NOT DISTINCT: only one overall flag per student (PostgreSQL 15+).
            models.UniqueConstraint(
                fields=["student", "subject"], nulls_distinct=False, name="shortage_flag_unique"
            ),
        ]

    def __str__(self):
        return f"{self.student} below threshold in {self.subject or 'overall'}"


class WeeklyShortageEmail(models.Model):
    """One Monday shortage email per faculty member per week, so a re-run cannot duplicate it."""

    faculty = models.ForeignKey(Faculty, on_delete=models.CASCADE, related_name="weekly_shortage_emails")
    week_start = models.DateField(help_text="Monday (IST) of the week the email belongs to.")
    student_count = models.PositiveIntegerField()
    sent_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["faculty", "week_start"], name="weekly_shortage_email_unique"),
        ]

    def __str__(self):
        return f"Shortage email to {self.faculty} for week of {self.week_start}"
