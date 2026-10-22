"""BL-14: authenticated student totals follow new marks and corrections."""

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.academics.models import Enrollment, Section, Subject, TeachingAssignment
from apps.academics.tests import make_faculty, make_student
from apps.accounts.models import Role, User

from .models import AttendanceRecord, Status
from .services import submit_attendance


class StudentAttendanceSummaryTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.student = make_student("S001")
        cls.other_student = make_student("S002")
        cls.faculty = make_faculty("F001")
        cls.admin = User.objects.create_user(username="ADMIN1", role=Role.ADMIN)
        section = Section.objects.create(class_name="CSE", name="A")
        subject = Subject.objects.create(code="CS101", name="Programming")
        cls.assignment = TeachingAssignment.objects.create(
            section=section, subject=subject, faculty=cls.faculty
        )
        for student in (cls.student, cls.other_student):
            Enrollment.objects.create(student=student, assignment=cls.assignment)

    def setUp(self):
        self.url = reverse("attendance_summary")
        self.client.force_login(self.student.user)

    def submit(self):
        return submit_attendance(
            actor=self.faculty.user,
            assignment=self.assignment,
            day=timezone.localdate(),
            period=1,
            statuses={self.student.pk: Status.PRESENT, self.other_student.pk: Status.ABSENT},
        )

    def test_new_marks_and_corrections_update_the_report(self):
        self.assertContains(self.client.get(self.url), "N/A – no classes yet")
        self.submit()
        self.assertContains(self.client.get(self.url), "1/1 (100.00%)")
        AttendanceRecord.objects.filter(student=self.student).update(status=Status.ABSENT)
        self.assertContains(self.client.get(self.url), "0/1 (0.00%)")

    def test_subject_and_overall_counts_are_displayed(self):
        self.submit()
        page = self.client.get(self.url)
        self.assertContains(page, "CS101")
        self.assertContains(page, "Programming")
        self.assertContains(page, "1/1 (100.00%)", count=2)
        self.assertIn("no-store", page["Cache-Control"])

    def test_query_parameters_cannot_select_another_student(self):
        self.submit()
        self.client.force_login(self.other_student.user)
        page = self.client.get(self.url, {"student": self.student.pk, "user": self.student.user_id})
        self.assertContains(page, "0/1 (0.00%)")
        self.assertNotContains(page, "S001")
        self.assertNotContains(page, "100.00%")

    def test_faculty_and_admin_cannot_open_student_only_report(self):
        for user in (self.faculty.user, self.admin):
            with self.subTest(role=user.role):
                self.client.force_login(user)
                self.assertEqual(self.client.get(self.url).status_code, 403)

    def test_anonymous_user_requires_login(self):
        self.client.logout()
        self.assertEqual(self.client.get(self.url).status_code, 302)

    def test_student_without_profile_gets_not_found(self):
        user = User.objects.create_user(username="NO_PROFILE", role=Role.STUDENT)
        self.client.force_login(user)
        self.assertEqual(self.client.get(self.url).status_code, 404)

    def test_dashboard_links_to_the_report(self):
        self.assertContains(self.client.get(reverse("dashboard_student")), self.url)
