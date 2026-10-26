"""BL-17/18: calendar boundaries, scoped corrections, settings and atomic audit."""

from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, date, datetime, timedelta
from threading import Barrier
from unittest.mock import patch

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError, close_old_connections, connection, connections, transaction
from django.test import TestCase, TransactionTestCase
from django.urls import reverse

from apps.academics.models import Enrollment, Faculty, Section, Student, Subject, TeachingAssignment
from apps.accounts.models import Role, User
from apps.audit import services as audit
from apps.audit.models import AuditEntry

from .calculations import student_attendance_summary
from .corrections import correct_attendance, update_correction_window
from .models import AttendanceRecord, AttendanceSession, CorrectionWindow, Status
from .services import submit_attendance

DAY = date(2026, 10, 6)
NOW = datetime(2026, 10, 8, 12, tzinfo=UTC)


class CorrectionFixtures:
    @classmethod
    def setUpTestData(cls):
        cls.admin = User.objects.create_user(username="ADMIN_CORR", role=Role.ADMIN)
        cls.teacher = User.objects.create_user(username="FAC_CORR", role=Role.FACULTY)
        cls.other_teacher = User.objects.create_user(username="FAC_OTHER", role=Role.FACULTY)
        cls.faculty = Faculty.objects.create(
            user=cls.teacher, faculty_id="FAC_CORR", full_name="Teacher", department="CSE"
        )
        cls.other_faculty = Faculty.objects.create(
            user=cls.other_teacher, faculty_id="FAC_OTHER", full_name="Other teacher", department="CSE"
        )
        student_user = User.objects.create_user(username="STU_CORR", role=Role.STUDENT)
        cls.student = Student.objects.create(user=student_user, roll_number="STU_CORR", full_name="Student")
        cls.assignment = TeachingAssignment.objects.create(
            section=Section.objects.create(class_name="CSE", name="A"),
            subject=Subject.objects.create(code="CORR", name="Corrections"),
            faculty=cls.faculty,
        )
        Enrollment.objects.create(student=cls.student, assignment=cls.assignment)
        cls.session = AttendanceSession.objects.create(
            assignment=cls.assignment,
            date=DAY,
            period=1,
            recorded_by=cls.teacher,
            recorded_by_code="FAC_CORR",
        )
        cls.record = AttendanceRecord.objects.create(
            session=cls.session, student=cls.student, status=Status.ABSENT
        )

    def correct(self, **updates):
        return correct_attendance(
            **{"actor": self.teacher, "record": self.record, "status": Status.PRESENT, **updates}
        )


class AttendanceCorrectionTests(CorrectionFixtures, TestCase):
    def setUp(self):
        clock = patch("django.utils.timezone.now", return_value=NOW)
        clock.start()
        self.addCleanup(clock.stop)

    def test_faculty_correction_persists_with_exact_audit_and_recorder_unchanged(self):
        saved = self.correct(reason="Attendance register checked")
        self.assertEqual(saved.pk, self.record.pk)
        self.record.refresh_from_db()
        self.assertEqual(self.record.status, Status.PRESENT)
        entry = AuditEntry.objects.get(action="attendance.correct")
        self.assertEqual((entry.target_type, entry.target_id), ("AttendanceRecord", str(self.record.pk)))
        self.assertEqual(entry.actor_user_id, self.teacher.pk)
        self.assertEqual(entry.actor_username, self.teacher.username)
        self.assertEqual(entry.timestamp, NOW)
        self.assertEqual(entry.old_value, {"status": Status.ABSENT})
        self.assertEqual(entry.new_value, {"status": Status.PRESENT})
        self.assertEqual(entry.reason, "Attendance register checked")
        self.assertFalse(entry.is_admin_override)
        self.session.refresh_from_db()
        self.assertEqual(self.session.recorded_by_id, self.teacher.pk)
        self.assertEqual(self.session.recorded_by_code, "FAC_CORR")

    def test_last_microsecond_of_second_day_ist_is_allowed(self):
        last_instant = datetime(2026, 10, 8, 18, 29, 59, 999999, tzinfo=UTC)
        with patch("django.utils.timezone.now", return_value=last_instant):
            self.correct()
        self.assertEqual(AttendanceRecord.objects.get(pk=self.record.pk).status, Status.PRESENT)

    def test_first_instant_of_third_day_ist_is_blocked(self):
        next_midnight = datetime(2026, 10, 8, 18, 30, tzinfo=UTC)
        with (
            patch("django.utils.timezone.now", return_value=next_midnight),
            self.assertRaisesMessage(ValidationError, "Correction window closed"),
        ):
            self.correct()
        self.assertEqual(AttendanceRecord.objects.get(pk=self.record.pk).status, Status.ABSENT)
        self.assertFalse(AuditEntry.objects.filter(action="attendance.correct").exists())

    def test_admin_override_after_deadline_requires_reason_and_is_logged(self):
        AttendanceSession.objects.filter(pk=self.session.pk).update(date=DAY - timedelta(days=40))
        with self.assertRaisesMessage(ValidationError, "requires a reason"):
            self.correct(actor=self.admin)
        self.correct(actor=self.admin, reason="  Medical evidence approved  ")
        entry = AuditEntry.objects.get(action="attendance.correct")
        self.assertTrue(entry.is_admin_override)
        self.assertEqual(entry.reason, "Medical evidence approved")
        self.assertEqual(entry.actor_user_id, self.admin.pk)

    def test_admin_override_is_logged_even_inside_the_faculty_window(self):
        self.correct(actor=self.admin, reason="Verified register")
        self.assertTrue(AuditEntry.objects.get(action="attendance.correct").is_admin_override)

    def test_student_other_faculty_and_inactive_cached_actor_are_denied(self):
        for actor in (self.student.user, self.other_teacher):
            with self.subTest(actor=actor), self.assertRaises(PermissionDenied):
                self.correct(actor=actor)
        User.objects.filter(pk=self.teacher.pk).update(is_active=False)
        with self.assertRaises(PermissionDenied):
            self.correct()
        self.assertFalse(AuditEntry.objects.filter(action="attendance.correct").exists())

    def test_changed_role_and_reassigned_class_are_rechecked_from_database(self):
        User.objects.filter(pk=self.teacher.pk).update(role=Role.STUDENT)
        with self.assertRaises(PermissionDenied):
            self.correct()
        User.objects.filter(pk=self.teacher.pk).update(role=Role.FACULTY)
        TeachingAssignment.objects.filter(pk=self.assignment.pk).update(faculty=self.other_faculty)
        with self.assertRaises(PermissionDenied):
            self.correct()

    def test_invalid_statuses_no_op_and_future_records_are_rejected_without_audit(self):
        for status in ("L", "", None, "Present", Status.ABSENT):
            with self.subTest(status=status), self.assertRaises(ValidationError):
                self.correct(status=status)
        AttendanceSession.objects.filter(pk=self.session.pk).update(date=date(2026, 10, 9))
        with self.assertRaisesMessage(ValidationError, "future"):
            self.correct(actor=self.admin, reason="Future session")
        self.assertEqual(AttendanceRecord.objects.get(pk=self.record.pk).status, Status.ABSENT)
        self.assertFalse(AuditEntry.objects.filter(action="attendance.correct").exists())

    def test_stale_record_status_is_not_used_as_audit_old_value(self):
        AttendanceRecord.objects.filter(pk=self.record.pk).update(status=Status.PRESENT)
        self.correct(status=Status.ABSENT)
        entry = AuditEntry.objects.get(action="attendance.correct")
        self.assertEqual(entry.old_value, {"status": Status.PRESENT})
        self.assertEqual(entry.new_value, {"status": Status.ABSENT})

    def test_audit_failure_after_insert_rolls_back_correction_and_audit(self):
        real_record = audit.record

        def failing_audit(*args, **kwargs):
            real_record(*args, **kwargs)
            raise IntegrityError("Injected audit failure")

        with (
            patch("apps.attendance.corrections.audit.record", side_effect=failing_audit),
            self.assertRaises(IntegrityError),
        ):
            self.correct()
        self.assertEqual(AttendanceRecord.objects.get(pk=self.record.pk).status, Status.ABSENT)
        self.assertFalse(AuditEntry.objects.filter(action="attendance.correct").exists())

    def test_saved_correction_updates_calculations_and_all_dashboards(self):
        self.assertEqual(student_attendance_summary(self.student).overall.display, "0/1 (0.00%)")
        self.correct()
        self.assertEqual(student_attendance_summary(self.student).overall.display, "1/1 (100.00%)")
        self.client.force_login(self.student.user)
        self.assertContains(self.client.get(reverse("dashboard_student")), "1/1 (100.00%)")
        self.client.force_login(self.teacher)
        self.assertContains(
            self.client.get(reverse("dashboard_faculty")),
            "Students below threshold in your assigned classes: 0",
        )
        self.client.force_login(self.admin)
        self.assertContains(
            self.client.get(reverse("dashboard_admin")), "Students below threshold overall: 0"
        )


class CorrectionWindowTests(CorrectionFixtures, TestCase):
    def setUp(self):
        clock = patch("django.utils.timezone.now", return_value=NOW)
        clock.start()
        self.addCleanup(clock.stop)

    def update(self, **updates):
        return update_correction_window(
            **{"actor": self.admin, "days": 0, "reason": "Institution correction policy", **updates}
        )

    def test_default_and_persisted_setting_have_complete_audit(self):
        self.assertEqual(CorrectionWindow.current_days(), 2)
        saved = self.update()
        self.assertEqual((saved.pk, saved.days), (1, 0))
        self.assertEqual(CorrectionWindow.current_days(), 0)
        entry = AuditEntry.objects.get(action="correction_window.update")
        self.assertEqual(entry.actor_user_id, self.admin.pk)
        self.assertEqual((entry.target_type, entry.target_id), ("CorrectionWindow", "1"))
        self.assertEqual(entry.old_value, {"days": 2})
        self.assertEqual(entry.new_value, {"days": 0})
        self.assertEqual(entry.reason, "Institution correction policy")

    def test_setting_requires_active_admin_reason_valid_integer_and_a_change(self):
        for actor in (self.teacher, self.student.user):
            with self.subTest(actor=actor), self.assertRaises(PermissionDenied):
                self.update(actor=actor)
        for days in (-1, 31, 2.5, "3", True, None, 2):
            with self.subTest(days=days), self.assertRaises(ValidationError):
                self.update(days=days)
        with self.assertRaises(ValidationError):
            self.update(reason="  ")
        User.objects.filter(pk=self.admin.pk).update(is_active=False)
        with self.assertRaises(PermissionDenied):
            self.update()
        self.assertEqual(CorrectionWindow.current_days(), 2)
        self.assertFalse(AuditEntry.objects.filter(action="correction_window.update").exists())

    def test_database_enforces_singleton_and_zero_to_thirty_range(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            CorrectionWindow.objects.create(pk=2, days=2)
        for days in (-1, 31):
            with self.subTest(days=days), self.assertRaises(IntegrityError), transaction.atomic():
                CorrectionWindow.objects.filter(pk=1).update(days=days)

    def test_zero_day_window_allows_only_today_for_correction_and_missed_submission(self):
        self.update(days=0)
        with self.assertRaisesMessage(ValidationError, "Correction window closed"):
            self.correct()
        AttendanceSession.objects.filter(pk=self.session.pk).update(date=date(2026, 10, 8))
        self.correct()
        for day, valid in ((date(2026, 10, 7), False), (date(2026, 10, 8), True)):
            values = {
                "actor": self.teacher,
                "assignment": self.assignment,
                "day": day,
                "period": 2,
                "statuses": {self.student.pk: Status.PRESENT},
            }
            if valid:
                self.assertTrue(submit_attendance(**values)[1])
            else:
                with self.assertRaisesMessage(ValidationError, "configured correction window"):
                    submit_attendance(**values)

    def test_thirty_day_window_allows_last_day_and_blocks_next_day(self):
        self.update(days=30)
        today = date(2026, 10, 8)
        AttendanceSession.objects.filter(pk=self.session.pk).update(date=today - timedelta(days=31))
        with self.assertRaisesMessage(ValidationError, "Correction window closed"):
            self.correct()
        AttendanceSession.objects.filter(pk=self.session.pk).update(date=today - timedelta(days=30))
        self.correct()
        session, created = submit_attendance(
            actor=self.teacher,
            assignment=self.assignment,
            day=today - timedelta(days=30),
            period=2,
            statuses={self.student.pk: Status.PRESENT},
        )
        self.assertTrue(created)
        self.assertEqual(session.date, today - timedelta(days=30))

    def test_audit_failure_after_insert_rolls_back_window_and_its_audit(self):
        real_record = audit.record

        def failing_audit(*args, **kwargs):
            real_record(*args, **kwargs)
            raise IntegrityError("Injected settings audit failure")

        with (
            patch("apps.attendance.corrections.audit.record", side_effect=failing_audit),
            self.assertRaises(IntegrityError),
        ):
            self.update()
        self.assertEqual(CorrectionWindow.current_days(), 2)
        self.assertFalse(AuditEntry.objects.filter(action="correction_window.update").exists())


class ConcurrentCorrectionTests(CorrectionFixtures, TransactionTestCase):
    def setUp(self):
        self.setUpTestData()
        self.second_admin = User.objects.create_user(username="ADMIN_CORR2", role=Role.ADMIN)
        CorrectionWindow.objects.update_or_create(pk=1, defaults={"days": 2})

    def _fixture_teardown(self):
        if connection.vendor != "postgresql":
            return super()._fixture_teardown()
        with connection.cursor() as cursor:
            cursor.execute("ALTER TABLE audit_auditentry DISABLE TRIGGER audit_entry_no_truncate")
        try:
            super()._fixture_teardown()
        finally:
            with connection.cursor() as cursor:
                cursor.execute("ALTER TABLE audit_auditentry ENABLE TRIGGER audit_entry_no_truncate")

    def test_concurrent_corrections_preserve_a_serial_audit_chain(self):
        if not connection.features.has_select_for_update:
            self.skipTest("Concurrent correction test requires PostgreSQL row locks")
        ready = Barrier(2)

        def worker(actor_pk, status):
            close_old_connections()
            try:
                actor = User.objects.get(pk=actor_pk)
                record = AttendanceRecord.objects.get(pk=self.record.pk)
                ready.wait(timeout=10)
                try:
                    correct_attendance(actor=actor, record=record, status=status, reason="Concurrent review")
                except ValidationError as error:
                    return "rejected", " ".join(error.messages)
                return "saved", status
            finally:
                connections.close_all()

        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [
                pool.submit(worker, self.admin.pk, Status.PRESENT),
                pool.submit(worker, self.second_admin.pk, Status.ABSENT),
            ]
            results = [future.result(timeout=20) for future in futures]
        self.assertGreaterEqual(sum(result[0] == "saved" for result in results), 1)
        entries = list(AuditEntry.objects.filter(action="attendance.correct").order_by("pk"))
        previous = Status.ABSENT
        for entry in entries:
            self.assertEqual(entry.old_value, {"status": previous})
            self.assertNotEqual(entry.old_value, entry.new_value)
            previous = entry.new_value["status"]
            self.assertTrue(entry.is_admin_override)
        self.assertEqual(len(entries), sum(result[0] == "saved" for result in results))
        self.assertEqual(AttendanceRecord.objects.get(pk=self.record.pk).status, previous)
