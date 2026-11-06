"""Snapshot validation and scheduler-command error paths (Part 3 coverage)."""

import copy
from io import StringIO
from unittest.mock import patch

from django.core.management import CommandError, call_command
from django.test import TestCase, override_settings

from apps.accounts.models import Role, User

from . import snapshots
from .locks import BackupBusy, BackupError

INVALID = "This backup is corrupt or incompatible with the current application schema."
USERS = User._meta.db_table


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class SnapshotValidationTests(TestCase):
    """A damaged or tampered snapshot must be rejected before any data is replaced."""

    @classmethod
    def setUpTestData(cls):
        User.objects.create_user(username="ADMIN1", password="Attend#2026", role=Role.ADMIN)

    def setUp(self):
        self.payload = snapshots.capture()

    def assert_rejected(self, payload, message=INVALID):
        with self.assertRaisesMessage(BackupError, message):
            snapshots.validate(payload)

    def test_captured_snapshot_is_valid(self):
        snapshots.validate(self.payload)

    def test_a_payload_that_is_not_an_object_is_rejected(self):
        self.assert_rejected(["not", "a", "snapshot"])

    def test_damaged_structures_are_rejected(self):
        def naive_time(p):
            p["created_at"] = "2026-11-06T10:00:00"

        def missing_time(p):
            del p["created_at"]

        def missing_table(p):
            p["tables"].pop(USERS)

        def table_not_a_list(p):
            p["tables"][USERS] = {}

        def row_with_extra_column(p):
            p["tables"][USERS][0]["unexpected"] = 1

        def duplicate_primary_key(p):
            p["tables"][USERS].append(dict(p["tables"][USERS][0]))

        for change in (
            naive_time,
            missing_time,
            missing_table,
            table_not_a_list,
            row_with_extra_column,
            duplicate_primary_key,
        ):
            with self.subTest(change=change.__name__):
                payload = copy.deepcopy(self.payload)
                change(payload)
                self.assert_rejected(payload)

    def test_a_snapshot_without_an_active_admin_is_rejected(self):
        payload = copy.deepcopy(self.payload)
        for row in payload["tables"][USERS]:
            row["is_active"] = False
        self.assert_rejected(
            payload, "The backup must contain an active Admin account with a usable password."
        )


class SchedulerCommandErrorTests(TestCase):
    target = "apps.backups.management.commands.run_scheduled_backups.run_due_backup"

    def test_busy_tick_waits_for_the_next_minute(self):
        out = StringIO()
        with patch(self.target, side_effect=BackupBusy("busy")):
            call_command("run_scheduled_backups", stdout=out)
        self.assertIn("Another operation is active", out.getvalue())

    def test_backup_failure_exits_with_the_safe_message(self):
        with (
            patch(self.target, side_effect=BackupError("Backup storage is unavailable.")),
            self.assertRaisesMessage(CommandError, "Backup storage is unavailable."),
        ):
            call_command("run_scheduled_backups", stdout=StringIO())
