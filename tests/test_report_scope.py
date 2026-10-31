"""BL-31 / UT_09_2: report generation requires an explicit scope and date range."""

from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from apps.academics.models import Subject, TeachingAssignment
from apps.attendance.models import AttendanceRecord, AttendanceSession, Status
from apps.audit.models import AuditEntry

from .support_integration import TEST_SETTINGS, IntegrationSupport, csv_rows


@override_settings(**TEST_SETTINGS)
class ReportScopeTests(IntegrationSupport, TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.make_fixture()
        session = AttendanceSession.objects.create(
            assignment=cls.assignment, date=timezone.localdate(), period=1
        )
        AttendanceRecord.objects.create(session=session, student=cls.students[0], status=Status.PRESENT)
        # Same section, another teacher: section filtering must not broaden authorization.
        shared = TeachingAssignment.objects.create(
            section=cls.section,
            subject=Subject.objects.create(code="SHARED101", name="Other teacher"),
            faculty=cls.other_assignment.faculty,
        )
        other_session = AttendanceSession.objects.create(
            assignment=shared, date=timezone.localdate(), period=1
        )
        AttendanceRecord.objects.create(session=other_session, student=cls.students[0], status=Status.ABSENT)

    def setUp(self):
        self.faculty = self.sign_in(self.faculty_user)

    def test_initial_report_page_shows_form_without_generating_or_offering_downloads(self):
        response = self.faculty.get(reverse("attendance_report"))
        self.assertContains(response, "Choose a report scope and date range")
        self.assertNotContains(response, "Download CSV")
        self.assertNotContains(response, "Report generated:")
        self.assertFalse(response.context["report_ready"])

    def test_blank_partial_or_missing_scope_cannot_generate_or_export(self):
        today = timezone.localdate().isoformat()
        invalid_queries = [
            {"start_date": "", "end_date": "", "assignment": ""},
            {"start_date": today, "end_date": today},
            {"assignment": self.assignment.pk},
            {"assignment": self.assignment.pk, "start_date": today},
            {"assignment": self.assignment.pk, "end_date": today},
        ]
        for route in ("attendance_report", "attendance_report_csv", "attendance_report_pdf"):
            for query in invalid_queries:
                with self.subTest(route=route, query=query):
                    response = self.faculty.get(reverse(route), query)
                    self.assertEqual(response.status_code, 400)
                    self.assertNotIn("Content-Disposition", response)
                    self.assertFalse(response.context["report_ready"])
                    self.assertNotContains(response, "Report generated:", status_code=400)
                    self.assertNotContains(response, "Download CSV", status_code=400)
        for route in ("attendance_report_csv", "attendance_report_pdf"):
            response = self.faculty.get(reverse(route))
            self.assertEqual(response.status_code, 400)
            self.assertNotIn("Content-Disposition", response)
            self.assertContains(response, "This field is required", status_code=400)
            self.assertContains(response, "Choose a report scope", status_code=400)
        self.assertFalse(AuditEntry.objects.filter(action="reports.export").exists())

    def test_explicit_section_and_all_scope_preserve_teacher_authorization(self):
        for filters in ({"section": self.section.pk, "all_records": ""}, {"all_records": "on"}):
            with self.subTest(filters=filters):
                query = self.report_params(**filters)
                response = self.faculty.get(reverse("attendance_report"), query)
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.context["overall"].display, "1/1 (100.00%)")
                rows = csv_rows(self.faculty.get(reverse("attendance_report_csv"), query))
                self.assertEqual(len(rows), 1)
                self.assertEqual(rows[0]["Subject Code"], self.subject.code)
                self.assertEqual(rows[0]["Attendance Percentage"], "100.00")

    def test_foreign_section_is_denied_for_html_and_both_exports(self):
        for route in ("attendance_report", "attendance_report_csv", "attendance_report_pdf"):
            with self.subTest(route=route):
                response = self.faculty.get(reverse(route), self.report_params(section=self.other_section.pk))
                self.assertEqual(response.status_code, 403)
                self.assertNotIn("Content-Disposition", response)
        self.assertEqual(AuditEntry.objects.filter(action="access.denied").count(), 3)

    def test_unsupported_export_format_does_not_produce_a_file(self):
        response = self.faculty.get("/attendance/reports/export/xlsx/", self.report_params())
        self.assertEqual(response.status_code, 404)
        self.assertNotIn("Content-Disposition", response)
