"""BL-13: idempotent retries, atomicity, and concurrent attendance submissions."""

from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from threading import Barrier
from unittest.mock import patch

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import (
    IntegrityError,
    OperationalError,
    close_old_connections,
    connection,
    connections,
    transaction,
)
from django.test import TestCase, TransactionTestCase
from django.urls import reverse
from django.utils import timezone

from apps.academics.models import Enrollment, Faculty, Section, Student, Subject, TeachingAssignment
from apps.accounts.models import Role, User
from apps.audit import services as audit
from apps.audit.models import AuditEntry

from .models import AttendanceRecord, AttendanceSession
from .services import submit_attendance


class SubmissionSetup:
    @classmethod
    def setUpTestData(cls):
        cls.teacher_user = User.objects.create_user(
            username="F003", password="Attend#2026", role=Role.FACULTY
        )
        faculty = Faculty.objects.create(
            user=cls.teacher_user, faculty_id="F003", full_name="Teacher", department="CSE"
        )
        subject = Subject.objects.create(code="CS202", name="Algorithms")
        section = Section.objects.create(class_name="CSE Year 2", name="C")
        cls.assignment = TeachingAssignment.objects.create(section=section, subject=subject, faculty=faculty)
        cls.students = []
        for roll in ("22CS001", "22CS002"):
            account = User.objects.create_user(username=roll, password="Attend#2026", role=Role.STUDENT)
            student = Student.objects.create(user=account, roll_number=roll, full_name=roll)
            Enrollment.objects.create(student=student, assignment=cls.assignment)
            cls.students.append(student)
        cls.day = timezone.localdate() - timedelta(days=1)

    def statuses(self):
        return {self.students[0].pk: "P", self.students[1].pk: "A"}

    def payload(self):
        return {
            "assignment": str(self.assignment.pk),
            "date": self.day.isoformat(),
            "period": "2",
            **{f"status_{student_id}": value for student_id, value in self.statuses().items()},
        }

    def submit(self, **updates):
        return submit_attendance(
            **{
                "actor": self.teacher_user,
                "assignment": self.assignment,
                "day": self.day,
                "period": 2,
                "statuses": self.statuses(),
                **updates,
            }
        )


class SubmissionSafetyTests(SubmissionSetup, TestCase):
    def test_inactive_actor_cannot_submit_using_a_cached_active_instance(self):
        User.objects.filter(pk=self.teacher_user.pk).update(is_active=False)
        self.assertTrue(self.teacher_user.is_active)
        with self.assertRaises(PermissionDenied):
            self.submit()
        self.assertFalse(AttendanceSession.objects.exists())

    def test_changed_role_cannot_submit_using_a_cached_faculty_instance(self):
        User.objects.filter(pk=self.teacher_user.pk).update(role=Role.STUDENT)
        with self.assertRaises(PermissionDenied):
            self.submit()
        self.assertFalse(AttendanceSession.objects.exists())

    def test_invalid_service_inputs_raise_validation_errors_without_partial_saves(self):
        for period in (None, "2", True, 0, 7):
            with self.subTest(period=period), self.assertRaises(ValidationError):
                self.submit(period=period)
        for statuses in (None, [], {str(self.students[0].pk): "P"}, {True: "P"}, {self.students[0].pk: "L"}):
            with self.subTest(statuses=statuses), self.assertRaises(ValidationError):
                self.submit(statuses=statuses)
        with self.assertRaises(ValidationError):
            self.submit(day=self.day.isoformat())
        self.assertFalse(AttendanceSession.objects.exists())
        self.assertFalse(AttendanceRecord.objects.exists())

    def test_repeated_status_fields_are_rejected_instead_of_using_the_last_value(self):
        self.client.force_login(self.teacher_user)
        data = self.payload()
        data[f"status_{self.students[0].pk}"] = ["A", "P"]
        response = self.client.post(reverse("attendance_mark"), data)
        self.assertContains(response, "exactly one attendance status", status_code=400)
        self.assertFalse(AttendanceSession.objects.exists())

    def test_malformed_status_fields_are_rejected_instead_of_ignored(self):
        self.client.force_login(self.teacher_user)
        for key in ("status_invalid", "status_", "status_01", "status_" + "9" * 100):
            with self.subTest(key=key):
                response = self.client.post(reverse("attendance_mark"), {**self.payload(), key: "P"})
                self.assertContains(response, "invalid student ID", status_code=400)
        self.assertFalse(AttendanceSession.objects.exists())

    def test_database_failure_has_clear_user_result_and_no_partial_attendance(self):
        self.client.force_login(self.teacher_user)
        with (
            patch.object(AttendanceRecord.objects, "bulk_create", side_effect=OperationalError("simulated")),
            self.assertLogs("apps.attendance.views", level="ERROR"),
        ):
            response = self.client.post(reverse("attendance_mark"), self.payload())
        self.assertContains(response, "No changes were saved", status_code=400)
        self.assertFalse(AttendanceSession.objects.exists())
        self.assertFalse(AttendanceRecord.objects.exists())

    def test_failure_after_audit_write_rolls_back_session_marks_and_audit(self):
        real_record = audit.record

        def failing_audit(*args, **kwargs):
            real_record(*args, **kwargs)
            raise IntegrityError("simulated audit failure")

        with (
            patch("apps.attendance.services.audit.record", side_effect=failing_audit),
            self.assertRaises(IntegrityError),
        ):
            self.submit()
        self.assertFalse(AttendanceSession.objects.exists())
        self.assertFalse(AttendanceRecord.objects.exists())
        self.assertFalse(AuditEntry.objects.filter(action="attendance.mark").exists())

    def test_database_uniqueness_guards_sessions_and_student_marks(self):
        session, _ = self.submit()
        with self.assertRaises(IntegrityError), transaction.atomic():
            AttendanceSession.objects.create(assignment=self.assignment, date=self.day, period=2)
        with self.assertRaises(IntegrityError), transaction.atomic():
            AttendanceRecord.objects.create(session=session, student=self.students[0], status="A")
        self.assertEqual(AttendanceSession.objects.count(), 1)
        self.assertEqual(AttendanceRecord.objects.count(), 2)

    def test_same_post_can_be_retried_without_new_rows(self):
        self.client.force_login(self.teacher_user)
        for _ in range(2):
            self.assertEqual(self.client.post(reverse("attendance_mark"), self.payload()).status_code, 302)
        self.assertEqual(AttendanceSession.objects.count(), 1)
        self.assertEqual(AttendanceRecord.objects.count(), 2)
        self.assertEqual(AuditEntry.objects.filter(action="attendance.mark").count(), 1)

    def test_changed_retry_cannot_overwrite_saved_values(self):
        submit_attendance(
            actor=self.teacher_user,
            assignment=self.assignment,
            day=self.day,
            period=2,
            statuses=self.statuses(),
        )
        self.client.force_login(self.teacher_user)
        data = self.payload()
        data[f"status_{self.students[0].pk}"] = "A"
        response = self.client.post(reverse("attendance_mark"), data)
        self.assertEqual(response.status_code, 400)
        self.assertContains(response, "already recorded", status_code=400)
        self.assertEqual(AttendanceRecord.objects.filter(status="P").count(), 1)
        self.assertEqual(AttendanceSession.objects.count(), 1)

    def test_failure_after_session_creation_rolls_back_everything(self):
        with patch.object(AttendanceRecord.objects, "bulk_create", side_effect=IntegrityError("simulated")):
            with self.assertRaises(IntegrityError):
                submit_attendance(
                    actor=self.teacher_user,
                    assignment=self.assignment,
                    day=self.day,
                    period=2,
                    statuses=self.statuses(),
                )
        self.assertFalse(AttendanceSession.objects.exists())
        self.assertFalse(AttendanceRecord.objects.exists())
        self.assertFalse(AuditEntry.objects.filter(action="attendance.mark").exists())

    def test_exact_retry_after_enrollment_change_does_not_duplicate(self):
        first, created = submit_attendance(
            actor=self.teacher_user,
            assignment=self.assignment,
            day=self.day,
            period=2,
            statuses=self.statuses(),
        )
        self.assertTrue(created)
        Enrollment.objects.filter(student=self.students[1], assignment=self.assignment).delete()
        second, created_again = submit_attendance(
            actor=self.teacher_user,
            assignment=self.assignment,
            day=self.day,
            period=2,
            statuses=self.statuses(),
        )
        self.assertFalse(created_again)
        self.assertEqual(first.pk, second.pk)
        self.assertEqual(AttendanceRecord.objects.count(), 2)


class ConcurrentSubmissionTests(SubmissionSetup, TransactionTestCase):
    """Uses separate database connections so SELECT FOR UPDATE is exercised on PostgreSQL."""

    def setUp(self):
        self.setUpTestData()

    def _fixture_teardown(self):
        if connection.vendor != "postgresql":
            return super()._fixture_teardown()
        # Permit Django to flush only its disposable test database. Production
        # audit protection remains intact, and the trigger is always restored.
        with connection.cursor() as cursor:
            cursor.execute("ALTER TABLE audit_auditentry DISABLE TRIGGER audit_entry_no_truncate")
        try:
            super()._fixture_teardown()
        finally:
            with connection.cursor() as cursor:
                cursor.execute("ALTER TABLE audit_auditentry ENABLE TRIGGER audit_entry_no_truncate")

    def simultaneous_submissions(self, statuses_list):
        if not connection.features.has_select_for_update:
            self.skipTest("Concurrent lock test requires PostgreSQL SELECT FOR UPDATE")
        barrier = Barrier(2)

        def worker(statuses):
            close_old_connections()
            try:
                actor = User.objects.get(pk=self.teacher_user.pk)
                assignment = TeachingAssignment.objects.get(pk=self.assignment.pk)
                barrier.wait(timeout=10)
                try:
                    session, created = submit_attendance(
                        actor=actor,
                        assignment=assignment,
                        day=self.day,
                        period=2,
                        statuses=statuses,
                    )
                except ValidationError as error:
                    return "rejected", " ".join(error.messages)
                return "saved", created
            finally:
                connections.close_all()

        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(worker, statuses) for statuses in statuses_list]
            return [future.result(timeout=20) for future in futures]

    def test_two_simultaneous_identical_requests_create_one_session(self):
        results = self.simultaneous_submissions([self.statuses(), self.statuses()])
        self.assertCountEqual(results, [("saved", True), ("saved", False)])
        self.assertEqual(AttendanceSession.objects.count(), 1)
        self.assertEqual(AttendanceRecord.objects.count(), 2)
        self.assertEqual(AuditEntry.objects.filter(action="attendance.mark").count(), 1)

    def test_two_conflicting_simultaneous_requests_keep_one_complete_winner(self):
        first = self.statuses()
        second = {self.students[0].pk: "A", self.students[1].pk: "P"}
        results = self.simultaneous_submissions([first, second])
        self.assertEqual([result[0] for result in results].count("saved"), 1)
        self.assertEqual([result[0] for result in results].count("rejected"), 1)
        self.assertIn("already recorded", next(result[1] for result in results if result[0] == "rejected"))
        self.assertEqual(AttendanceSession.objects.count(), 1)
        self.assertEqual(AttendanceRecord.objects.count(), 2)
        saved = dict(AttendanceRecord.objects.values_list("student_id", "status"))
        self.assertIn(saved, [first, second])
        self.assertEqual(AuditEntry.objects.filter(action="attendance.mark").count(), 1)
