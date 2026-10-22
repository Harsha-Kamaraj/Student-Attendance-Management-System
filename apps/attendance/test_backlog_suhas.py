"""Regression tests for BL-15, BL-22, and BL-25 (assigned backlog issues #15/#22/#25)."""

import datetime

from django.test import TestCase
from django.urls import reverse

from apps.academics.models import Enrollment, Section, Subject, TeachingAssignment
from apps.academics.tests import make_faculty, make_student
from apps.accounts.models import Role, User

from .calculations import attendance_shortage_statistics, student_attendance_summary
from .models import AttendanceRecord, AttendanceSession, AttendanceThreshold, Status

PASSWORD = "Attend#2026"
A, F, S = Role.ADMIN, Role.FACULTY, Role.STUDENT


class BacklogFeatureTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = User.objects.create_user(username="ADMIN1", password=PASSWORD, role=A)
        cls.faculty = make_faculty("F001")
        cls.student = make_student("21CS001")
        cls.other_student = make_student("21CS002")
        cls.section = Section.objects.create(class_name="B.Tech CSE Year 2", name="A")
        cls.subject = Subject.objects.create(code="CS101", name="Programming")
        cls.other_subject = Subject.objects.create(code="MA101", name="Mathematics")
        cls.assignment = TeachingAssignment.objects.create(
            section=cls.section, subject=cls.subject, faculty=cls.faculty
        )
        cls.other_assignment = TeachingAssignment.objects.create(
            section=cls.section, subject=cls.other_subject, faculty=cls.faculty
        )
        for student in (cls.student, cls.other_student):
            Enrollment.objects.create(student=student, assignment=cls.assignment)
            Enrollment.objects.create(student=student, assignment=cls.other_assignment)

    def add_record(self, student, assignment, day, status, period=1):
        session, _ = AttendanceSession.objects.get_or_create(
            assignment=assignment, date=day, period=period
        )
        return AttendanceRecord.objects.create(session=session, student=student, status=status)

    def test_student_report_filters_by_subject_and_inclusive_date_range(self):
        self.add_record(self.student, self.assignment, datetime.date(2026, 10, 1), Status.PRESENT)
        self.add_record(self.student, self.assignment, datetime.date(2026, 10, 2), Status.ABSENT, period=2)
        self.add_record(self.student, self.other_assignment, datetime.date(2026, 10, 2), Status.PRESENT)
        self.client.force_login(self.student.user)
        response = self.client.get(
            reverse("attendance_summary"),
            {
                "subject": self.subject.pk,
                "start_date": "2026-10-02",
                "end_date": "2026-10-02",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "0/1 (0.00%)")
        self.assertNotContains(response, '<tr><th scope="row">MA101')

    def test_student_report_shows_empty_state_for_date_with_no_records(self):
        self.add_record(self.student, self.assignment, datetime.date(2026, 10, 1), Status.PRESENT)
        self.client.force_login(self.student.user)
        response = self.client.get(
            reverse("attendance_summary"), {"start_date": "2026-10-10", "end_date": "2026-10-11"}
        )
        self.assertContains(response, "No attendance records match these filters.")

    def test_student_report_rejects_reversed_date_range(self):
        self.client.force_login(self.student.user)
        response = self.client.get(
            reverse("attendance_summary"), {"start_date": "2026-10-12", "end_date": "2026-10-10"}
        )
        self.assertContains(response, "End date must be on or after the start date.")

    def test_threshold_defaults_to_75_and_admin_can_change_it(self):
        self.assertEqual(AttendanceThreshold.current_value(), 75)
        self.client.force_login(self.admin)
        response = self.client.post(reverse("threshold_settings"), {"value": "80"})
        self.assertRedirects(response, reverse("threshold_settings"))
        self.assertEqual(AttendanceThreshold.current_value(), 80)

    def test_threshold_rejects_values_outside_one_to_one_hundred(self):
        self.client.force_login(self.admin)
        for value in ("0", "101", "74.5", "abc"):
            with self.subTest(value=value):
                response = self.client.post(reverse("threshold_settings"), {"value": value})
                self.assertEqual(response.status_code, 400)
                self.assertEqual(AttendanceThreshold.current_value(), 75)

    def test_only_admin_can_change_threshold(self):
        for user in (self.faculty.user, self.student.user):
            with self.subTest(role=user.role):
                self.client.force_login(user)
                self.assertEqual(self.client.get(reverse("threshold_settings")).status_code, 403)
                self.assertEqual(
                    self.client.post(reverse("threshold_settings"), {"value": "90"}).status_code, 403
                )
        self.assertEqual(AttendanceThreshold.current_value(), 75)

    def test_shortage_counts_use_exact_ratio_equality_and_ignore_zero_records(self):
        # S1: 2/3 is below 75%; S2: exactly 3/4 is not below; no-record subjects are ignored.
        self.add_record(self.student, self.assignment, datetime.date(2026, 10, 1), Status.PRESENT)
        self.add_record(self.student, self.assignment, datetime.date(2026, 10, 2), Status.ABSENT, period=2)
        self.add_record(self.student, self.assignment, datetime.date(2026, 10, 3), Status.PRESENT, period=3)
        for period, status in enumerate(
            (Status.PRESENT, Status.PRESENT, Status.PRESENT, Status.ABSENT), start=1
        ):
            self.add_record(
                self.other_student,
                self.assignment,
                datetime.date(2026, 10, 4),
                status,
                period=period,
            )
        stats = attendance_shortage_statistics(threshold=75)
        self.assertEqual(stats["threshold"], 75)
        self.assertEqual(stats["subject_shortages"], 1)
        self.assertEqual(stats["students_below_overall"], 1)

    def test_dashboard_statistics_are_role_scoped_and_present(self):
        self.add_record(self.student, self.assignment, datetime.date(2026, 10, 1), Status.ABSENT)
        self.client.force_login(self.admin)
        admin_page = self.client.get(reverse("dashboard_admin"))
        self.assertContains(admin_page, "Attendance threshold: 75%")
        self.assertContains(admin_page, "Students below threshold overall: 1")

        self.client.force_login(self.faculty.user)
        faculty_page = self.client.get(reverse("dashboard_faculty"))
        self.assertContains(faculty_page, "Subject-level shortage cases in your assigned classes: 1")

        self.client.force_login(self.student.user)
        student_page = self.client.get(reverse("dashboard_student"))
        self.assertContains(student_page, "Attendance threshold")
        self.assertContains(student_page, "Your overall attendance is below the threshold.")

    def test_attendance_summary_recalculates_after_record_correction(self):
        record = self.add_record(
            self.student, self.assignment, datetime.date(2026, 10, 1), Status.ABSENT
        )
        before = student_attendance_summary(self.student)
        self.assertEqual(before.overall.display, "0/1 (0.00%)")
        record.status = Status.PRESENT
        record.save(update_fields=["status"])
        after = student_attendance_summary(self.student)
        self.assertEqual(after.overall.display, "1/1 (100.00%)")
