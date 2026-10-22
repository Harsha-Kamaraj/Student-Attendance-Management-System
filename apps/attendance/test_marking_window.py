"""BL-12 fix: faculty may record missed sessions only within the correction window.

BL-01 D-09, AR-06, AR-08, UC-06 1c; test plan ST_06_3 and ST_06_4.
"""

from datetime import timedelta

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.academics.models import Enrollment, Faculty, Section, Student, Subject, TeachingAssignment
from apps.accounts.models import Role, User

from .models import CORRECTION_WINDOW_DAYS, AttendanceSession, Status
from .services import submit_attendance

PASSWORD = "Attend#2026"


class FacultyDateWindowTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.faculty_user = User.objects.create_user(username="F001", password=PASSWORD, role=Role.FACULTY)
        cls.admin = User.objects.create_user(username="ADMIN1", password=PASSWORD, role=Role.ADMIN)
        faculty = Faculty.objects.create(
            user=cls.faculty_user, faculty_id="F001", full_name="Teacher One", department="CSE"
        )
        cls.assignment = TeachingAssignment.objects.create(
            section=Section.objects.create(class_name="CSE Year 2", name="A"),
            subject=Subject.objects.create(code="CS101", name="Programming"),
            faculty=faculty,
        )
        user = User.objects.create_user(username="21CS001", password=PASSWORD, role=Role.STUDENT)
        cls.student = Student.objects.create(user=user, roll_number="21CS001", full_name="Student One")
        Enrollment.objects.create(student=cls.student, assignment=cls.assignment)

    def days_ago(self, days):
        return timezone.localdate() - timedelta(days=days)

    def submit(self, actor, days, reason=""):
        return submit_attendance(
            actor=actor,
            assignment=self.assignment,
            day=self.days_ago(days),
            period=1,
            statuses={self.student.pk: Status.PRESENT},
            reason=reason,
        )

    def test_window_is_two_days(self):
        self.assertEqual(CORRECTION_WINDOW_DAYS, 2)

    def test_faculty_can_record_on_the_last_day_of_the_window(self):
        # ST_06_3: session 2 days ago is still inside the window
        session, created = self.submit(self.faculty_user, CORRECTION_WINDOW_DAYS)
        self.assertTrue(created)

    def test_faculty_cannot_record_the_day_after_the_window(self):
        # ST_06_4, UC-06 1c
        with self.assertRaisesMessage(ValidationError, "outside the 2-day correction window"):
            self.submit(self.faculty_user, CORRECTION_WINDOW_DAYS + 1)
        self.assertFalse(AttendanceSession.objects.exists())

    def test_faculty_cannot_record_a_month_ago(self):
        with self.assertRaises(ValidationError):
            self.submit(self.faculty_user, 30)
        self.assertFalse(AttendanceSession.objects.exists())

    def test_admin_can_record_an_old_missed_session_with_a_reason(self):
        # AR-08
        session, created = self.submit(self.admin, 40, reason="Session was not recorded")
        self.assertTrue(created)

    def test_form_tells_faculty_before_they_fill_in_the_roster(self):
        self.client.login(username="F001", password=PASSWORD)
        old = self.days_ago(CORRECTION_WINDOW_DAYS + 1).isoformat()
        response = self.client.get(
            reverse("attendance_mark"), {"assignment": self.assignment.pk, "date": old, "period": 1}
        )
        self.assertContains(response, "outside the 2-day correction window")
        self.assertContains(response, "Contact the Admin")
        self.assertNotContains(response, "Save complete attendance")

    def test_posting_an_old_date_saves_nothing(self):
        self.client.login(username="F001", password=PASSWORD)
        old = self.days_ago(CORRECTION_WINDOW_DAYS + 1).isoformat()
        self.client.post(
            reverse("attendance_mark"),
            {"assignment": self.assignment.pk, "date": old, "period": 1, f"status_{self.student.pk}": "P"},
        )
        self.assertFalse(AttendanceSession.objects.exists())
