"""BL-13: idempotent retries, atomicity, and concurrent attendance submissions."""

from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from threading import Barrier
from unittest.mock import patch

from django.db import IntegrityError, close_old_connections, connection
from django.test import TestCase, TransactionTestCase
from django.urls import reverse
from django.utils import timezone

from apps.academics.models import Enrollment, Faculty, Section, Student, Subject, TeachingAssignment
from apps.accounts.models import Role, User
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


class SubmissionSafetyTests(SubmissionSetup, TestCase):
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

    def test_two_simultaneous_identical_requests_create_one_session(self):
        if not connection.features.has_select_for_update:
            self.skipTest("Concurrent lock test requires PostgreSQL SELECT FOR UPDATE")
        barrier = Barrier(2)

        def worker():
            close_old_connections()
            try:
                barrier.wait(timeout=10)
                return submit_attendance(
                    actor=self.teacher_user,
                    assignment=self.assignment,
                    day=self.day,
                    period=2,
                    statuses=self.statuses(),
                )[1]
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(worker) for _ in range(2)]
            created = [future.result(timeout=20) for future in futures]
        self.assertCountEqual(created, [True, False])
        self.assertEqual(AttendanceSession.objects.count(), 1)
        self.assertEqual(AttendanceRecord.objects.count(), 2)
