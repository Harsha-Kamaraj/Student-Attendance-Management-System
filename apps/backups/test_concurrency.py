"""Use separate PostgreSQL connections to exercise the operation and maintenance gates."""

from concurrent.futures import ThreadPoolExecutor
from datetime import time, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Barrier, Event
from unittest.mock import patch

from cryptography.fernet import Fernet
from django.db import close_old_connections, connection, connections
from django.test import TransactionTestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import Role, User

from . import services, snapshots
from .locks import MAINTENANCE_LOCK, BackupBusy, database_lock
from .models import Backup, BackupSchedule


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"], OTP_REQUIRED=False)
class BackupConcurrencyTests(TransactionTestCase):
    def setUp(self):
        folder = TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        config = override_settings(
            BACKUP_DIRECTORY=Path(folder.name) / "backups",
            BACKUP_ENCRYPTION_KEY=Fernet.generate_key().decode(),
        )
        config.enable()
        self.addCleanup(config.disable)
        self.admin = User.objects.create_user(
            username="BACKUP_ADMIN", role=Role.ADMIN, password="Attend#2026"
        )
        self.client.force_login(self.admin)

    def _fixture_teardown(self):
        with connection.cursor() as cursor:
            cursor.execute("ALTER TABLE audit_auditentry DISABLE TRIGGER audit_entry_no_truncate")
        try:
            super()._fixture_teardown()
        finally:
            with connection.cursor() as cursor:
                cursor.execute("ALTER TABLE audit_auditentry ENABLE TRIGGER audit_entry_no_truncate")

    def test_two_due_workers_make_only_one_scheduled_backup(self):
        services.configure_schedule(actor=self.admin, enabled=True, time=time(8))
        BackupSchedule.objects.update(next_run_at=timezone.now() - timedelta(minutes=1))
        ready = Barrier(2)

        def worker():
            close_old_connections()
            try:
                ready.wait(timeout=10)
                try:
                    result = services.run_due_backup()
                    return "complete" if result else "not_due"
                except BackupBusy:
                    return "busy"
            finally:
                connections.close_all()

        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(worker) for _ in range(2)]
            outcomes = [future.result(timeout=20) for future in futures]
        self.assertEqual(outcomes.count("complete"), 1)
        self.assertEqual(
            Backup.objects.filter(kind=Backup.Kind.SCHEDULED, status=Backup.Status.COMPLETE).count(), 1
        )

    def test_restore_refuses_to_start_while_an_authenticated_request_is_active(self):
        backup = services.create_backup(actor=self.admin)
        acquired, release = Event(), Event()

        def request_worker():
            close_old_connections()
            try:
                with database_lock(MAINTENANCE_LOCK, shared=True):
                    acquired.set()
                    if not release.wait(timeout=10):
                        raise TimeoutError("Test did not release request")
            finally:
                connections.close_all()

        with ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(request_worker)
            try:
                self.assertTrue(acquired.wait(timeout=10))
                with self.assertRaises(BackupBusy):
                    services.restore_backup(actor=self.admin, backup=backup, password="Attend#2026")
                self.assertEqual(Backup.objects.count(), 1)
            finally:
                release.set()
            future.result(timeout=10)

    def test_requests_are_blocked_during_real_restore_and_old_session_is_revoked(self):
        backup = services.create_backup(actor=self.admin)
        restoring, finish = Event(), Event()
        original = snapshots._insert_rows

        def paused_insert(table, rows):
            if not restoring.is_set():
                restoring.set()
                if not finish.wait(timeout=10):
                    raise TimeoutError("Test did not release restore")
            original(table, rows)

        def worker():
            close_old_connections()
            try:
                services.restore_backup(actor=self.admin, backup=backup, password="Attend#2026")
            finally:
                connections.close_all()

        with patch("apps.backups.snapshots._insert_rows", side_effect=paused_insert):
            with ThreadPoolExecutor(max_workers=1) as pool:
                future = pool.submit(worker)
                try:
                    self.assertTrue(restoring.wait(timeout=10))
                    response = self.client.get(reverse("dashboard_admin"))
                    self.assertEqual(response.status_code, 503)
                    self.assertEqual(response["Retry-After"], "30")
                finally:
                    finish.set()
                future.result(timeout=10)
        response = self.client.get(reverse("dashboard_admin"))
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith(reverse("login")))
        self.assertEqual(self.client.get(reverse("home")).status_code, 200)
