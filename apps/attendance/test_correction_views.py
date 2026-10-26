"""BL-17 UI: scoped corrections, Admin reasons, settings, and CSRF."""

from datetime import UTC, date, datetime, timedelta
from unittest.mock import patch

from django.db import OperationalError
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from apps.academics.models import Enrollment, Section, Subject, TeachingAssignment
from apps.academics.tests import make_faculty, make_student
from apps.accounts.models import Role, User
from apps.audit.models import AuditEntry

from .models import AttendanceRecord, AttendanceSession, CorrectionWindow, Status
from .services import earliest_faculty_date


class AttendanceCorrectionViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = User.objects.create_user(username="ADMIN1", role=Role.ADMIN)
        cls.faculty = make_faculty("F001")
        cls.other_faculty = make_faculty("F002")
        cls.student = make_student("S001")
        section = Section.objects.create(class_name="CSE", name="A")
        subject = Subject.objects.create(code="CS101", name="Programming")
        cls.assignment = TeachingAssignment.objects.create(
            section=section, subject=subject, faculty=cls.faculty
        )
        Enrollment.objects.create(student=cls.student, assignment=cls.assignment)
        session = AttendanceSession.objects.create(
            assignment=cls.assignment,
            date=timezone.localdate(),
            period=1,
            recorded_by=cls.faculty.user,
            recorded_by_code=cls.faculty.faculty_id,
        )
        cls.record = AttendanceRecord.objects.create(
            session=session, student=cls.student, status=Status.ABSENT
        )

    def setUp(self):
        self.url = reverse("attendance_correct", args=[self.record.pk])
        self.client.force_login(self.faculty.user)

    def test_faculty_opens_and_corrects_own_record(self):
        page = self.client.get(self.url)
        self.assertContains(page, "S001")
        self.assertContains(page, "23:59:59 IST")
        self.assertIn("no-store", page["Cache-Control"])
        saved = self.client.post(self.url, {"status": "P", "reason": "Marked absent by mistake"})
        self.assertRedirects(saved, reverse("attendance_changes", args=[self.record.pk]))
        self.record.refresh_from_db()
        self.assertEqual(self.record.status, Status.PRESENT)
        audit = AuditEntry.objects.get(action="attendance.correct")
        self.assertEqual(audit.old_value, {"status": "A"})
        self.assertEqual(audit.new_value, {"status": "P"})
        self.assertEqual(audit.actor_user_id, self.faculty.user_id)
        self.assertEqual(audit.reason, "Marked absent by mistake")

    def test_closed_window_is_read_only_and_direct_post_is_rejected(self):
        AttendanceSession.objects.filter(pk=self.record.session_id).update(
            date=timezone.localdate() - timedelta(days=3)
        )
        page = self.client.get(self.url)
        self.assertContains(page, "correction window is closed")
        self.assertNotContains(page, "Save correction")
        self.assertEqual(self.client.post(self.url, {"status": "P"}).status_code, 200)
        self.record.refresh_from_db()
        self.assertEqual(self.record.status, Status.ABSENT)
        self.assertFalse(AuditEntry.objects.filter(action="attendance.correct").exists())

    def test_display_and_missed_session_window_keep_ist_when_active_timezone_is_utc(self):
        AttendanceSession.objects.filter(pk=self.record.session_id).update(date=date(2026, 10, 6))
        # 9 Oct 00:00 IST: the 6 Oct session has expired, although UTC is still 8 Oct.
        with (
            patch("django.utils.timezone.now", return_value=datetime(2026, 10, 8, 18, 30, tzinfo=UTC)),
            timezone.override("UTC"),
        ):
            self.assertFalse(self.client.get(self.url).context["can_edit"])
            self.assertEqual(earliest_faculty_date(), date(2026, 10, 7))

    def test_admin_old_record_requires_reason_and_is_logged_as_override(self):
        AttendanceSession.objects.filter(pk=self.record.session_id).update(
            date=timezone.localdate() - timedelta(days=40)
        )
        self.client.force_login(self.admin)
        for reason in ("", "   "):
            self.assertContains(self.client.post(self.url, {"status": "P", "reason": reason}), "required")
        self.record.refresh_from_db()
        self.assertEqual(self.record.status, Status.ABSENT)
        self.assertEqual(
            self.client.post(self.url, {"status": "P", "reason": "Approved correction"}).status_code, 302
        )
        entry = AuditEntry.objects.get(action="attendance.correct")
        self.assertTrue(entry.is_admin_override)
        self.assertEqual(entry.reason, "Approved correction")

    def test_other_faculty_and_student_cannot_read_or_correct(self):
        for user in (self.other_faculty.user, self.student.user):
            self.client.force_login(user)
            with self.subTest(user=user.username):
                self.assertEqual(self.client.get(self.url).status_code, 403)
                self.assertEqual(self.client.post(self.url, {"status": "P"}).status_code, 403)
        self.record.refresh_from_db()
        self.assertEqual(self.record.status, Status.ABSENT)
        self.assertFalse(AuditEntry.objects.filter(action="attendance.correct").exists())

    def test_invalid_status_and_no_change_are_not_saved_as_corrections(self):
        for status in ("", "L", "A"):
            with self.subTest(status=status):
                self.assertEqual(self.client.post(self.url, {"status": status}).status_code, 200)
        self.assertFalse(AuditEntry.objects.filter(action="attendance.correct").exists())
        self.record.refresh_from_db()
        self.assertEqual(self.record.status, Status.ABSENT)

    def test_success_updates_student_dashboard_and_report(self):
        self.client.post(self.url, {"status": "P"})
        self.client.force_login(self.student.user)
        self.assertContains(self.client.get(reverse("attendance_summary")), "1/1 (100.00%)")
        self.assertContains(self.client.get(reverse("dashboard_student")), "1/1 (100.00%)")

    def test_database_failure_has_clear_feedback(self):
        with (
            patch("apps.attendance.correction_views.correct_attendance", side_effect=OperationalError),
            self.assertLogs("apps.attendance.correction_views", level="ERROR"),
        ):
            page = self.client.post(self.url, {"status": "P"})
        self.assertContains(page, "No changes were saved")
        self.record.refresh_from_db()
        self.assertEqual(self.record.status, Status.ABSENT)

    def test_missing_record_is_404(self):
        self.assertEqual(self.client.get(reverse("attendance_correct", args=[999999])).status_code, 404)

    def test_csrf_required(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.faculty.user)
        self.assertEqual(client.post(self.url, {"status": "P"}).status_code, 403)


class CorrectionWindowSettingsViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = User.objects.create_user(username="ADMIN1", role=Role.ADMIN)
        cls.faculty = make_faculty("F001")
        cls.student = make_student("S001")

    def setUp(self):
        self.url = reverse("correction_window_settings")
        self.client.force_login(self.admin)

    def test_default_and_valid_zero_and_thirty_day_policies_persist(self):
        self.assertEqual(self.client.get(self.url).context["form"]["days"].value(), 2)
        for days in (0, 30):
            with self.subTest(days=days):
                response = self.client.post(self.url, {"days": days, "reason": "Approved policy"})
                self.assertRedirects(response, self.url)
                self.assertEqual(CorrectionWindow.current_days(), days)

    def test_invalid_days_and_blank_reason_do_not_change_the_policy(self):
        for data in (
            {"days": -1, "reason": "Invalid"},
            {"days": 31, "reason": "Invalid"},
            {"days": "1.5", "reason": "Invalid"},
            {"days": 0, "reason": "   "},
            {},
        ):
            with self.subTest(data=data):
                self.assertEqual(self.client.post(self.url, data).status_code, 200)
                self.assertEqual(CorrectionWindow.current_days(), 2)

    def test_faculty_and_student_are_denied(self):
        for user in (self.faculty.user, self.student.user):
            self.client.force_login(user)
            self.assertEqual(self.client.get(self.url).status_code, 403)
            self.assertEqual(self.client.post(self.url, {"days": 30, "reason": "Tampered"}).status_code, 403)
        self.assertEqual(CorrectionWindow.current_days(), 2)

    def test_csrf_and_login_are_required(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.admin)
        self.assertEqual(client.post(self.url, {"days": 0, "reason": "Change"}).status_code, 403)
        self.client.logout()
        self.assertEqual(self.client.get(self.url).status_code, 302)
