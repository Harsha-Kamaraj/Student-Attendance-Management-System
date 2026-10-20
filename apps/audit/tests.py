from django.db import DatabaseError, transaction
from django.test import TestCase

from apps.accounts.models import Role, User

from .models import AuditEntry


class AuditEntryTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(username="admin1", password="Attend#2026", role=Role.ADMIN)
        self.entry = AuditEntry.objects.create(
            actor_user_id=self.admin.pk,
            actor_username=self.admin.username,
            action="attendance.correct",
            target_type="AttendanceRecord",
            target_id="42",
            old_value={"status": "A"},
            new_value={"status": "P"},
            reason="Student submitted medical certificate",
            is_admin_override=True,
        )

    def test_entry_is_saved_with_old_and_new_values(self):
        entry = AuditEntry.objects.get(pk=self.entry.pk)
        self.assertEqual(entry.old_value, {"status": "A"})
        self.assertEqual(entry.new_value, {"status": "P"})
        self.assertTrue(entry.is_admin_override)

    def test_entry_cannot_be_changed_through_the_model(self):
        self.entry.reason = "edited"
        with self.assertRaises(PermissionError):
            self.entry.save()

    def test_entry_cannot_be_deleted_through_the_model(self):
        with self.assertRaises(PermissionError):
            self.entry.delete()

    def test_database_rejects_bulk_update(self):
        with transaction.atomic(), self.assertRaises(DatabaseError):
            AuditEntry.objects.filter(pk=self.entry.pk).update(reason="edited")

    def test_database_rejects_bulk_delete(self):
        with transaction.atomic(), self.assertRaises(DatabaseError):
            AuditEntry.objects.filter(pk=self.entry.pk).delete()

    def test_entry_survives_deleting_the_actor(self):
        self.admin.delete()
        entry = AuditEntry.objects.get(pk=self.entry.pk)
        self.assertEqual(entry.actor_username, "ADMIN1")
