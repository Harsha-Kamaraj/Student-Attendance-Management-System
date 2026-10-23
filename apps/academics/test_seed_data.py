"""BL-28: the loadable test dataset matches Documents/Test_Data_Fixture.md exactly."""

import datetime
from io import StringIO

from django.core.management import CommandError, call_command
from django.test import TestCase, override_settings
from django.urls import reverse

from apps.accounts.models import Role, User
from apps.attendance.calculations import attendance_shortage_statistics, student_attendance_summary
from apps.attendance.models import AttendanceRecord, AttendanceSession

from .models import Enrollment, Faculty, Section, Student, TeachingAssignment

D = datetime.date


@override_settings(DEBUG=True)
class SeedTestDataTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        with override_settings(DEBUG=True):
            call_command("seed_test_data", stdout=StringIO())

    def summary(self, roll, **filters):
        return student_attendance_summary(Student.objects.get(roll_number=roll), **filters)

    def displays(self, roll, **filters):
        summary = self.summary(roll, **filters)
        return {row.subject.code: row.display for row in summary.subjects}, summary.overall.display

    def test_counts(self):
        self.assertEqual(User.objects.filter(role=Role.ADMIN).count(), 1)
        self.assertEqual(Faculty.objects.count(), 3)
        self.assertEqual(Student.objects.count(), 4)
        self.assertEqual(Section.objects.count(), 2)
        self.assertEqual(AttendanceSession.objects.count(), 103)
        self.assertEqual(AttendanceRecord.objects.count(), 303)

    def test_every_account_logs_in_with_the_documented_password(self):
        for username in ("ADMIN1", "F001", "F002", "F003", "S001", "S002", "S003", "S004"):
            with self.subTest(user=username):
                user = User.objects.get(username=username)
                self.assertTrue(user.check_password("Attend#2026"))
                self.assertFalse(user.must_change_password)

    def test_student_totals(self):
        self.assertEqual(
            self.displays("S001"), ({"CS101": "74/100 (74.00%)", "MA101": "2/3 (66.67%)"}, "76/103 (73.79%)")
        )
        self.assertEqual(self.displays("S002"), ({"CS101": "75/100 (75.00%)"}, "75/100 (75.00%)"))
        self.assertEqual(self.displays("S004"), ({"CS101": "76/100 (76.00%)"}, "76/100 (76.00%)"))
        self.assertEqual(self.displays("S003"), ({"MA101": "N/A – no classes yet"}, "N/A – no classes yet"))

    def test_threshold_boundaries_at_75(self):
        self.assertTrue(self.summary("S001").overall.is_below_threshold(75))
        self.assertFalse(self.summary("S002").overall.is_below_threshold(75))
        self.assertFalse(self.summary("S004").overall.is_below_threshold(75))
        self.assertFalse(self.summary("S003").overall.is_below_threshold(75))

    def test_shortage_counts(self):
        def counts(**kwargs):
            stats = attendance_shortage_statistics(**kwargs)
            return stats["students_below_overall"], stats["subject_shortages"]

        self.assertEqual(counts(threshold=75), (1, 2))
        self.assertEqual(counts(threshold=80), (3, 4))
        for code, expected in (("F001", (1, 1)), ("F002", (1, 1)), ("F003", (0, 0))):
            with self.subTest(faculty=code):
                own = TeachingAssignment.objects.filter(faculty__faculty_id=code)
                self.assertEqual(counts(assignments=own, threshold=75), expected)

    def test_date_filters(self):
        subject = TeachingAssignment.objects.get(subject__code="MA101").subject_id
        one_day = self.summary("S001", subject_id=subject, start_date=D(2026, 10, 2), end_date=D(2026, 10, 2))
        self.assertEqual(one_day.overall.display, "0/1 (0.00%)")
        two_days = self.summary(
            "S001", subject_id=subject, start_date=D(2026, 10, 2), end_date=D(2026, 10, 3)
        )
        self.assertEqual(two_days.overall.display, "1/2 (50.00%)")
        empty = self.summary("S001", start_date=D(2026, 10, 10), end_date=D(2026, 10, 11))
        self.assertEqual(empty.overall.held, 0)

    def test_cs101_sessions_are_all_in_june_2026(self):
        dates = AttendanceSession.objects.filter(assignment__subject__code="CS101").values_list(
            "date", flat=True
        )
        self.assertEqual((min(dates), max(dates)), (D(2026, 6, 1), D(2026, 6, 17)))

    def test_rosters(self):
        def roster(code):
            return set(
                Enrollment.objects.filter(assignment__faculty__faculty_id=code).values_list(
                    "student__roll_number", flat=True
                )
            )

        self.assertEqual(roster("F001"), {"S001", "S002", "S004"})
        self.assertEqual(roster("F002"), {"S001", "S003"})
        self.assertEqual(roster("F003"), set())

    def test_admin_dashboard_shows_documented_figures(self):
        self.client.login(username="ADMIN1", password="Attend#2026")
        context = self.client.get(reverse("dashboard_admin")).context
        self.assertEqual(
            (
                context["student_count"],
                context["faculty_count"],
                context["section_count"],
                context["session_count"],
            ),
            (4, 3, 2, 103),
        )

    def test_refuses_to_run_twice(self):
        with self.assertRaisesMessage(CommandError, "already loaded"):
            call_command("seed_test_data", stdout=StringIO())
        self.assertEqual(Student.objects.count(), 4)


class SeedSafetyTests(TestCase):
    @override_settings(DEBUG=False)
    def test_refuses_when_debug_is_off(self):
        with self.assertRaisesMessage(CommandError, "DEBUG is off"):
            call_command("seed_test_data", stdout=StringIO())
        self.assertFalse(User.objects.exists())
