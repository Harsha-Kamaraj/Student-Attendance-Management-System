"""Server-side guards in attendance marking, correction and window settings (Part 3 coverage).

The web pages normally prevent these inputs; the services must still refuse them when called directly.
"""

from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import DatabaseError
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.academics.models import Enrollment, Section, Subject, TeachingAssignment
from apps.academics.tests import make_faculty, make_student
from apps.accounts.models import Role, User
from apps.audit.models import AuditEntry

from .corrections import correct_attendance, update_correction_window
from .models import AttendanceRecord, AttendanceSession, CorrectionWindow, Status
from .services import submit_attendance

PASSWORD = "Attend#2026"


class AttendanceGuardTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(username="ADMIN1", password=PASSWORD, role=Role.ADMIN)
        self.member = make_faculty("F001")
        self.teacher = self.member.user
        section = Section.objects.create(class_name="B.Tech CSE Year 2", name="A")
        subject = Subject.objects.create(code="CS101", name="Programming")
        self.assignment = TeachingAssignment.objects.create(
            section=section, subject=subject, faculty=self.member
        )
        self.today = timezone.localdate()

    def submit(self, **overrides):
        values = {
            "actor": self.teacher,
            "assignment": self.assignment,
            "day": self.today,
            "period": 1,
            "statuses": {},
        }
        values.update(overrides)
        return submit_attendance(**values)

    def test_marking_requires_a_signed_in_account_that_still_exists(self):
        for actor in (AnonymousUser(), User(pk=999_999, username="GONE", role=Role.FACULTY)):
            with self.subTest(actor=actor), self.assertRaises(PermissionDenied):
                self.submit(actor=actor)

    def test_marking_refuses_a_future_date_even_without_the_date_picker(self):
        with self.assertRaisesMessage(ValidationError, "Attendance cannot be recorded for a future date."):
            self.submit(day=self.today + timedelta(days=1))

    def test_marking_reason_must_be_text(self):
        with self.assertRaisesMessage(ValidationError, "The attendance reason must be text."):
            self.submit(reason=None)

    def test_marking_a_class_with_no_active_students_is_refused(self):
        with self.assertRaisesMessage(ValidationError, "No active enrolled students exist for this class."):
            self.submit()
        self.assertFalse(AttendanceSession.objects.exists())

    def test_correction_requires_a_signed_in_account_and_an_existing_record(self):
        student = make_student("S001")
        Enrollment.objects.create(student=student, assignment=self.assignment)
        session = AttendanceSession.objects.create(assignment=self.assignment, date=self.today, period=1)
        record = AttendanceRecord.objects.create(session=session, student=student, status=Status.ABSENT)
        with self.assertRaises(PermissionDenied):
            correct_attendance(actor=AnonymousUser(), record=record, status=Status.PRESENT)
        with self.assertRaisesMessage(ValidationError, "This attendance record no longer exists."):
            correct_attendance(actor=self.teacher, record=AttendanceRecord(pk=999_999), status=Status.PRESENT)
        record.refresh_from_db()
        self.assertEqual(record.status, Status.ABSENT)

    def test_correction_window_reason_must_be_text(self):
        with self.assertRaisesMessage(ValidationError, "The reason must be text."):
            update_correction_window(actor=self.admin, days=5, reason=None)
        self.assertEqual(CorrectionWindow.current_days(), 2)


class CorrectionWindowPageErrorTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(username="ADMIN1", password=PASSWORD, role=Role.ADMIN)
        self.client.force_login(self.admin)
        self.url = reverse("correction_window_settings")

    def test_saving_the_current_value_explains_that_nothing_changed(self):
        response = self.client.post(self.url, {"days": CorrectionWindow.current_days(), "reason": "Review"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "already has this value")
        self.assertFalse(AuditEntry.objects.filter(action="correction_window.update").exists())

    def test_a_database_failure_is_reported_and_logged_without_saving(self):
        with (
            patch("apps.attendance.correction_views.update_correction_window", side_effect=DatabaseError),
            self.assertLogs("apps.attendance.correction_views", level="ERROR"),
        ):
            response = self.client.post(self.url, {"days": 5, "reason": "Exam week"})
        self.assertContains(response, "The correction window could not be saved. No changes were saved.")
        self.assertEqual(CorrectionWindow.current_days(), 2)
