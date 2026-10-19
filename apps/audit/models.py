"""Append-only audit history of attendance and account changes (SEC-16, SEC-21)."""

from django.db import models


class AuditEntry(models.Model):
    """One logged action. Entries are never updated or deleted.

    The actor is stored as an ID and username, not a foreign key, so entries
    survive when the user is permanently deleted (BL-01 D-04). A database
    trigger (migration 0002) rejects any UPDATE or DELETE.
    """

    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    actor_user_id = models.BigIntegerField(null=True, blank=True)
    actor_username = models.CharField(max_length=150, blank=True)
    action = models.CharField(max_length=50)
    target_type = models.CharField(max_length=50)
    target_id = models.CharField(max_length=50)
    old_value = models.JSONField(null=True, blank=True)
    new_value = models.JSONField(null=True, blank=True)
    reason = models.TextField(blank=True)
    is_admin_override = models.BooleanField(default=False)

    class Meta:
        verbose_name_plural = "audit entries"
        ordering = ["-timestamp"]

    def __str__(self):
        return f"{self.timestamp:%Y-%m-%d %H:%M} {self.actor_username} {self.action} {self.target_type}"

    def save(self, *args, **kwargs):
        if not self._state.adding:
            raise PermissionError("Audit entries cannot be changed.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise PermissionError("Audit entries cannot be deleted.")
