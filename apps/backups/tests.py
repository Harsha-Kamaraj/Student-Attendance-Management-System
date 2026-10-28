"""BL-26/27 acceptance and failure recovery against a disposable PostgreSQL database."""

import json
import os
from datetime import UTC, datetime, time, timedelta
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from cryptography.fernet import Fernet
from django.contrib.sessions.models import Session
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.db import DatabaseError, IntegrityError, connection, transaction
from django.test import Client, TestCase, override_settings
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone

from apps.academics.models import Enrollment, Faculty, Section, Student, Subject, TeachingAssignment
from apps.accounts.models import OTPBackupCode, OTPEmailCode, Role, User
from apps.attendance.calculations import student_attendance_summary
from apps.attendance.models import AttendanceRecord, AttendanceSession, AttendanceThreshold, Status
from apps.audit.models import AuditEntry
from apps.notifications.models import Notification, ShortageFlag, WeeklyShortageEmail

from . import services, storage
from .locks import BackupError
from .models import Backup, BackupSchedule

PASSWORD = "Attend#2026"


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class BackupTests(TestCase):
    def setUp(self):
        folder = TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.root = Path(folder.name) / "backups"
        self.config = override_settings(
            BACKUP_DIRECTORY=self.root,
            BACKUP_ENCRYPTION_KEY=Fernet.generate_key().decode(),
            OTP_REQUIRED=False,
        )
        self.config.enable()
        self.addCleanup(self.config.disable)
        self.admin = User.objects.create_user(username="RECOVERY_ADMIN", role=Role.ADMIN, password=PASSWORD)
        self.teacher = User.objects.create_user(username="RECOVERY_FAC", role=Role.FACULTY, password=PASSWORD)
        self.student_user = User.objects.create_user(
            username="RECOVERY_STU", role=Role.STUDENT, password=PASSWORD
        )
        self.student = Student.objects.create(
            user=self.student_user, roll_number="RECOVERY_STU", full_name="Test Student"
        )
        faculty = Faculty.objects.create(
            user=self.teacher, faculty_id="RECOVERY_FAC", full_name="Test Faculty", department="CSE"
        )
        section = Section.objects.create(class_name="CSE", name="A")
        subject = Subject.objects.create(code="RECOVERY", name="Recovery Test")
        assignment = TeachingAssignment.objects.create(faculty=faculty, section=section, subject=subject)
        Enrollment.objects.create(student=self.student, assignment=assignment)
        session = AttendanceSession.objects.create(assignment=assignment, date=timezone.localdate(), period=1)
        self.record = AttendanceRecord.objects.create(
            student=self.student, session=session, status=Status.PRESENT
        )
        AttendanceThreshold.objects.create(pk=1, value=80)
        self.client.force_login(self.admin)

    def backup(self):
        return services.create_backup(actor=self.admin)

    def restore(self, backup, **kwargs):
        return services.restore_backup(
            actor=self.admin, backup=backup, password=kwargs.get("password", PASSWORD)
        )

    def test_manual_backup_has_encrypted_private_file_checksum_and_complete_data(self):
        response = self.client.post(reverse("backup_create"))
        self.assertRedirects(response, reverse("backup_list"))
        backup = Backup.objects.get()
        self.assertEqual(backup.status, Backup.Status.COMPLETE)
        path = self.root / backup.filename
        token = path.read_bytes()
        self.assertNotIn(b"RECOVERY_STU", token)
        self.assertNotIn(PASSWORD.encode(), token)
        self.assertEqual(os.stat(path).st_mode & 0o777, 0o600)
        self.assertEqual(os.stat(self.root).st_mode & 0o777, 0o700)
        self.assertEqual(backup.checksum, storage.checksum(token))
        payload = storage.decrypt(token)
        self.assertEqual(payload["tables"]["attendance_attendancerecord"][0]["status"], "P")
        self.assertEqual(len(payload["tables"]["accounts_user"]), 3)
        self.assertNotIn("django_session", payload["tables"])
        self.assertFalse(any(name.startswith("backups_") for name in payload["tables"]))
        self.assertTrue(AuditEntry.objects.filter(action="backup.success").exists())

    def test_backup_list_and_encrypted_download_persist_after_relogin(self):
        backup = self.backup()
        self.client.logout()
        self.client.force_login(self.admin)
        page = self.client.get(reverse("backup_list"))
        self.assertContains(page, str(backup.pk))
        self.assertContains(page, backup.checksum)
        response = self.client.get(reverse("backup_download", args=[backup.pk]))
        self.assertEqual(response.content, (self.root / backup.filename).read_bytes())
        self.assertIn("no-store", response["Cache-Control"])

    def test_failed_write_keeps_last_valid_backup_and_logs_failure(self):
        valid = self.backup()
        token = (self.root / valid.filename).read_bytes()
        with patch("apps.backups.storage.publish", side_effect=OSError("private disk path")):
            response = self.client.post(reverse("backup_create"), follow=True)
        self.assertContains(response, "Backup failed")
        self.assertNotContains(response, "private disk path")
        self.assertEqual((self.root / valid.filename).read_bytes(), token)
        self.assertEqual(Backup.objects.filter(status=Backup.Status.COMPLETE).count(), 1)
        self.assertEqual(Backup.objects.filter(status=Backup.Status.FAILED).count(), 1)
        self.assertTrue(AuditEntry.objects.filter(action="backup.failure").exists())

    def test_missing_encryption_key_fails_without_plaintext_fallback(self):
        with override_settings(BACKUP_ENCRYPTION_KEY=""):
            response = self.client.post(reverse("backup_create"), follow=True)
        self.assertContains(response, "Configure a valid backup encryption key")
        self.assertFalse(self.root.exists())

    def test_public_storage_and_symlinks_are_refused(self):
        with override_settings(BACKUP_DIRECTORY=Path(__file__).resolve().parents[2] / "static" / "backup"):
            with self.assertRaises(BackupError):
                self.backup()
        self.root.symlink_to(self.root.parent, target_is_directory=True)
        with self.assertRaises(BackupError):
            self.backup()

    def test_size_limit_fails_without_destroying_existing_backup(self):
        valid = self.backup()
        with override_settings(BACKUP_MAX_BYTES=100):
            with self.assertRaises(BackupError):
                self.backup()
        self.assertTrue((self.root / valid.filename).exists())

    def test_unauthorized_roles_cannot_list_create_schedule_download_import_or_restore(self):
        backup = self.backup()
        for user in (self.teacher, self.student_user):
            self.client.force_login(user)
            for name, args in (
                ("backup_list", []),
                ("backup_create", []),
                ("backup_schedule", []),
                ("backup_import", []),
                ("backup_download", [backup.pk]),
                ("backup_restore", [backup.pk]),
            ):
                with self.subTest(user=user.username, route=name):
                    self.assertEqual(self.client.get(reverse(name, args=args)).status_code, 403)
                    self.assertEqual(
                        self.client.post(
                            reverse(name, args=args), {"password": PASSWORD, "confirm": "on"}
                        ).status_code,
                        403,
                    )
        self.assertEqual(Backup.objects.count(), 1)
        self.assertTrue(AuditEntry.objects.filter(action="access.denied").exists())

    def test_service_rechecks_role_and_active_status(self):
        User.objects.filter(pk=self.admin.pk).update(is_active=False)
        with self.assertRaises(PermissionDenied):
            self.backup()

    def test_mutations_require_csrf_and_backup_creation_requires_post(self):
        backup = self.backup()
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.admin)
        for name, args in (
            ("backup_create", []),
            ("backup_schedule", []),
            ("backup_import", []),
            ("backup_restore", [backup.pk]),
        ):
            self.assertEqual(
                client.post(reverse(name, args=args), {"password": PASSWORD, "confirm": "on"}).status_code,
                403,
            )
        self.assertEqual(self.client.get(reverse("backup_create")).status_code, 405)

    def test_restore_recovers_deleted_student_login_attendance_and_percentages(self):
        backup = self.backup()
        User.objects.filter(pk=self.student_user.pk).delete()
        AttendanceThreshold.objects.filter(pk=1).update(value=50)
        self.assertFalse(Student.objects.filter(pk=self.student.pk).exists())
        safety = self.restore(backup)
        restored = Student.objects.get(pk=self.student.pk)
        self.assertTrue(restored.user.check_password(PASSWORD))
        self.assertEqual(student_attendance_summary(restored).overall.display, "1/1 (100.00%)")
        self.assertEqual(Enrollment.objects.filter(student=restored).count(), 1)
        self.assertEqual(AttendanceThreshold.current_value(), 80)
        self.assertEqual(safety.kind, Backup.Kind.SAFETY)
        self.assertTrue(AuditEntry.objects.filter(action="restore.success").exists())

    def test_restore_requires_password_and_explicit_confirmation(self):
        backup = self.backup()
        url = reverse("backup_restore", args=[backup.pk])
        self.assertContains(self.client.post(url, {"password": PASSWORD}), "This field is required")
        self.assertContains(
            self.client.post(url, {"password": "wrong", "confirm": "on"}), "password was not accepted"
        )
        self.assertEqual(Backup.objects.count(), 1)
        self.assertFalse(AuditEntry.objects.filter(action="restore.success").exists())

    def test_password_reauthentication_obeys_lockout(self):
        backup = self.backup()
        for _ in range(5):
            with self.assertRaises(ValidationError):
                self.restore(backup, password="wrong")
        with self.assertRaises(ValidationError):
            self.restore(backup)
        self.assertEqual(Backup.objects.count(), 1)

    def test_checksum_corruption_is_rejected_before_safety_backup_or_data_change(self):
        backup = self.backup()
        with (self.root / backup.filename).open("ab") as stream:
            stream.write(b"tampered")
        with self.assertRaisesMessage(BackupError, "checksum"):
            self.restore(backup)
        self.assertEqual(Backup.objects.count(), 1)
        self.record.refresh_from_db()
        self.assertEqual(self.record.status, "P")

    def test_authenticated_encryption_detects_tampering_even_if_checksum_is_replaced(self):
        backup = self.backup()
        token = bytearray((self.root / backup.filename).read_bytes())
        token[len(token) // 2] ^= 1
        (self.root / backup.filename).write_bytes(token)
        backup.checksum = storage.checksum(token)
        backup.save()
        with self.assertRaisesMessage(BackupError, "integrity"):
            self.restore(backup)
        self.assertEqual(Backup.objects.count(), 1)

    def test_incompatible_schema_is_refused_before_current_data_changes(self):
        backup = self.backup()
        payload = storage.decrypt(storage.read(backup))
        payload["migrations"].append(["future", "0001"])
        token = storage.encrypt(payload)
        with self.assertRaisesMessage(BackupError, "incompatible"):
            services.import_backup(actor=self.admin, token=token)
        self.assertEqual(Backup.objects.count(), 1)

    def test_invalid_foreign_key_rolls_back_every_restored_table(self):
        backup = self.backup()
        payload = storage.decrypt(storage.read(backup))
        payload["tables"]["attendance_attendancerecord"][0]["student_id"] = 999999
        imported = services.import_backup(actor=self.admin, token=storage.encrypt(payload))
        AttendanceThreshold.objects.filter(pk=1).update(value=65)
        with self.assertRaisesMessage(BackupError, "Current data is unchanged"):
            self.restore(imported)
        self.assertEqual(AttendanceThreshold.current_value(), 65)
        self.record.refresh_from_db()
        self.assertEqual(self.record.student_id, self.student.pk)
        self.assertFalse(AuditEntry.objects.filter(action="restore.success").exists())

    def test_failed_safety_backup_aborts_restore(self):
        backup = self.backup()
        AttendanceThreshold.objects.filter(pk=1).update(value=65)
        with patch("apps.backups.storage.publish", side_effect=OSError("disk full")):
            with self.assertRaises(BackupError):
                self.restore(backup)
        self.assertEqual(AttendanceThreshold.current_value(), 65)

    def test_audit_failure_rolls_back_restore_and_keeps_safety_backup(self):
        backup = self.backup()
        AttendanceThreshold.objects.filter(pk=1).update(value=65)
        original = services.record_event

        def fail_success(action, **kwargs):
            if action == "restore.success":
                raise IntegrityError("simulated failure")
            return original(action, **kwargs)

        with patch("apps.backups.services.record_event", side_effect=fail_success):
            with self.assertRaises(BackupError):
                self.restore(backup)
        self.assertEqual(AttendanceThreshold.current_value(), 65)
        self.assertEqual(
            Backup.objects.filter(kind=Backup.Kind.SAFETY, status=Backup.Status.COMPLETE).count(), 1
        )

    def test_restore_preserves_live_audit_and_does_not_duplicate_snapshot_history(self):
        entry = AuditEntry.objects.create(
            action="test.before", target_type="User", target_id=self.student_user.pk
        )
        backup = self.backup()
        later = AuditEntry.objects.create(
            action="test.after", target_type="User", target_id=self.student_user.pk
        )
        self.restore(backup)
        self.restore(backup)
        self.assertTrue(AuditEntry.objects.filter(pk=entry.pk).exists())
        self.assertTrue(AuditEntry.objects.filter(pk=later.pk).exists())
        self.assertEqual(AuditEntry.objects.filter(action="test.before").count(), 1)
        with self.assertRaises(DatabaseError), transaction.atomic():
            AuditEntry.objects.filter(pk=entry.pk).update(reason="tamper")

    def test_restore_invalidates_sessions_email_and_backup_codes(self):
        OTPBackupCode.objects.create(user=self.student_user, code_hash="hashed")
        OTPEmailCode.objects.create(
            user=self.student_user, code_hash="hashed", expires_at=timezone.now() + timedelta(minutes=10)
        )
        backup = self.backup()
        session_key = self.client.session.session_key
        previous_hash = self.admin.get_session_auth_hash()
        response = self.client.post(
            reverse("backup_restore", args=[backup.pk]), {"password": PASSWORD, "confirm": "on"}
        )
        self.assertRedirects(response, reverse("login"))
        self.assertFalse(Session.objects.filter(session_key=session_key).exists())
        self.assertFalse(OTPEmailCode.objects.exists())
        self.assertFalse(OTPBackupCode.objects.filter(used_at__isnull=True).exists())
        self.admin.refresh_from_db()
        self.assertNotEqual(previous_hash, self.admin.get_session_auth_hash())
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_sequences_allow_creating_records_after_restore(self):
        backup = self.backup()
        later = User.objects.create_user(username="LATER", role=Role.STUDENT)
        deleted_pk = later.pk
        later.delete()
        self.restore(backup)
        user = User.objects.create_user(username="AFTER", role=Role.STUDENT)
        self.assertGreater(user.pk, deleted_pk)

    def test_restore_recovers_notification_relationships_and_delivery_state(self):
        notification = Notification.objects.create(
            recipient=self.student_user, title="Low attendance", body="Test notification"
        )
        flag = ShortageFlag.objects.create(student=self.student)
        delivery = WeeklyShortageEmail.objects.create(
            faculty=Faculty.objects.get(user=self.teacher),
            week_start=timezone.localdate(),
            student_count=1,
        )
        expected_ids = (notification.pk, flag.pk, delivery.pk)
        backup = self.backup()
        Notification.objects.all().delete()
        ShortageFlag.objects.all().delete()
        WeeklyShortageEmail.objects.all().delete()
        self.restore(backup)
        self.assertEqual(Notification.objects.get(pk=expected_ids[0]).recipient_id, self.student_user.pk)
        self.assertEqual(ShortageFlag.objects.get(pk=expected_ids[1]).student_id, self.student.pk)
        self.assertEqual(WeeklyShortageEmail.objects.get(pk=expected_ids[2]).faculty.user_id, self.teacher.pk)

    def test_unavailable_storage_reports_failure_without_changing_data(self):
        backup = self.backup()
        with patch("apps.backups.storage.directory", side_effect=OSError("private storage path")):
            response = self.client.get(reverse("backup_download", args=[backup.pk]), follow=True)
            self.assertContains(response, "The backup file is unavailable")
            with self.assertRaisesMessage(BackupError, "The backup file is unavailable"):
                self.restore(backup)
        self.assertTrue(User.objects.filter(pk=self.student_user.pk).exists())
        self.assertTrue(AuditEntry.objects.filter(action="restore.failure").exists())

    def test_restore_does_not_put_decrypted_secrets_in_debug_query_logs(self):
        secret = "JBSWY3DPEHPK3PXPJBSWY3DPEHPK3PXP"
        User.objects.filter(pk=self.student_user.pk).update(otp_secret=secret)
        backup = self.backup()
        with CaptureQueriesContext(connection) as queries:
            self.restore(backup)
        self.assertNotIn(secret, " ".join(item["sql"] for item in queries))

    def test_imported_audit_events_are_appended_without_replacing_live_events(self):
        entry = AuditEntry.objects.create(action="test.live", target_type="User", target_id=self.admin.pk)
        backup = self.backup()
        payload = storage.decrypt(storage.read(backup))
        copied = next(row.copy() for row in payload["tables"]["audit_auditentry"] if row["id"] == entry.pk)
        copied["action"] = "test.from_other_database"
        payload["tables"]["audit_auditentry"] = [copied]
        imported = services.import_backup(actor=self.admin, token=storage.encrypt(payload))
        self.restore(imported)
        self.assertEqual(AuditEntry.objects.filter(action="test.from_other_database").count(), 1)
        self.assertEqual(AuditEntry.objects.get(pk=entry.pk).action, "test.live")

    def test_import_validates_encrypted_file_without_restoring(self):
        backup = self.backup()
        AttendanceThreshold.objects.filter(pk=1).update(value=65)
        upload = SimpleUploadedFile("saved.sambak", storage.read(backup))
        response = self.client.post(reverse("backup_import"), {"backup_file": upload})
        self.assertRedirects(response, reverse("backup_list"))
        self.assertEqual(AttendanceThreshold.current_value(), 65)
        self.assertEqual(Backup.objects.filter(kind=Backup.Kind.IMPORTED).count(), 1)
        with self.assertRaises(BackupError):
            services.import_backup(
                actor=self.admin, token=json.dumps({"sql": "DROP TABLE accounts_user"}).encode()
            )

    def test_schedule_requires_valid_time_and_admin_can_disable_it(self):
        url = reverse("backup_schedule")
        self.assertContains(
            self.client.post(url, {"enabled": "on", "time": ""}), "Choose a daily backup time"
        )
        self.assertContains(self.client.post(url, {"enabled": "on", "time": "25:00"}), "Enter a valid time")
        self.assertFalse(BackupSchedule.objects.exists())
        self.assertRedirects(
            self.client.post(url, {"enabled": "on", "time": "08:00"}), reverse("backup_list")
        )
        self.assertTrue(BackupSchedule.objects.get().enabled)
        self.client.post(url, {})
        self.assertFalse(BackupSchedule.objects.get().enabled)

    def test_daily_schedule_uses_ist_and_next_day_at_exact_boundary(self):
        now = datetime(2026, 10, 28, 2, 29, tzinfo=UTC)
        self.assertEqual(services.next_daily(time(8), now).astimezone(UTC), now + timedelta(minutes=1))
        self.assertEqual(services.next_daily(time(8), now + timedelta(minutes=1)).day, 29)

    def test_due_worker_runs_once_and_schedule_survives_restore(self):
        services.configure_schedule(actor=self.admin, enabled=True, time=time(8))
        BackupSchedule.objects.update(next_run_at=timezone.now() - timedelta(minutes=1))
        output = StringIO()
        call_command("run_scheduled_backups", stdout=output)
        backup = Backup.objects.get(kind=Backup.Kind.SCHEDULED)
        self.assertEqual(backup.status, Backup.Status.COMPLETE)
        self.assertIsNone(services.run_due_backup())
        schedule = BackupSchedule.objects.get()
        self.assertIsNotNone(schedule.last_success_at)
        self.restore(backup)
        schedule.refresh_from_db()
        self.assertTrue(schedule.enabled)
        self.assertEqual(schedule.time, time(8))

    def test_scheduler_failure_retries_after_15_minutes_and_retains_previous_backup(self):
        valid = self.backup()
        services.configure_schedule(actor=self.admin, enabled=True, time=time(8))
        BackupSchedule.objects.update(next_run_at=timezone.now() - timedelta(minutes=1))
        with patch("apps.backups.storage.publish", side_effect=OSError("disk full")):
            with self.assertRaises(BackupError):
                services.run_due_backup()
        schedule = BackupSchedule.objects.get()
        self.assertTrue(schedule.last_error)
        self.assertGreater(schedule.next_run_at, timezone.now() + timedelta(minutes=14))
        self.assertTrue((self.root / valid.filename).exists())
        self.assertIsNone(services.run_due_backup())

    def test_interrupted_jobs_are_failed_on_next_operation(self):
        interrupted = Backup.objects.create(kind=Backup.Kind.MANUAL)
        self.backup()
        interrupted.refresh_from_db()
        self.assertEqual(interrupted.status, Backup.Status.FAILED)
        self.assertIn("interrupted", interrupted.error)
