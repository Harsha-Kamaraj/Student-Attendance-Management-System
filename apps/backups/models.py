import uuid

from django.db import models


class Backup(models.Model):
    class Status(models.TextChoices):
        RUNNING = "running", "Running"
        COMPLETE = "complete", "Complete"
        FAILED = "failed", "Failed"

    class Kind(models.TextChoices):
        MANUAL = "manual", "Manual"
        SCHEDULED = "scheduled", "Scheduled"
        SAFETY = "safety", "Before restore"
        IMPORTED = "imported", "Imported"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    snapshot_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    kind = models.CharField(max_length=12, choices=Kind.choices)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.RUNNING)
    requested_by = models.CharField(max_length=150, blank=True)
    checksum = models.CharField(max_length=64, blank=True)
    size = models.PositiveBigIntegerField(default=0)
    row_counts = models.JSONField(default=dict)
    error = models.CharField(max_length=250, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.get_kind_display()} backup {self.pk} ({self.status})"

    @property
    def filename(self):
        return f"{self.pk}.sambak"


class BackupSchedule(models.Model):
    id = models.PositiveSmallIntegerField(primary_key=True, default=1, editable=False)
    enabled = models.BooleanField(default=False)
    time = models.TimeField(null=True, blank=True)
    next_run_at = models.DateTimeField(null=True, blank=True)
    last_attempt_at = models.DateTimeField(null=True, blank=True)
    last_success_at = models.DateTimeField(null=True, blank=True)
    last_error = models.CharField(max_length=250, blank=True)
    updated_by = models.CharField(max_length=150, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.CheckConstraint(condition=models.Q(pk=1), name="backup_schedule_singleton"),
            models.CheckConstraint(
                condition=models.Q(enabled=False) | models.Q(time__isnull=False, next_run_at__isnull=False),
                name="backup_schedule_requires_time",
            ),
        ]

    def __str__(self):
        return f"Daily backup at {self.time} IST" if self.enabled else "Scheduled backups disabled"
