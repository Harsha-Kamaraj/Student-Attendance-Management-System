"""BL-31: complete journeys across accounts, attendance, reports, alerts and recovery.

Traceability: IT_01_1-5/ST_01_6, IT_02_1, IT_03_1, IT_05_1-3,
IT_06_1-3, IT_07_1-3, IT_08_1-5, IT_09_1-3, IT_10_1-7,
IT_11_1-3, IT_12_1-3, IT_13_1-3 and IT_34_1-3 in the refined test plan.
All people/addresses are synthetic; mail is captured locally and backups use a
temporary private directory and a new, test-only encryption key.
"""

import re
from datetime import datetime, timedelta
from pathlib import Path
from smtplib import SMTPException
from tempfile import TemporaryDirectory
from unittest.mock import patch
from uuid import uuid4
from zoneinfo import ZoneInfo

from cryptography.fernet import Fernet
from django.contrib.sessions.models import Session
from django.core import mail
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError, connection
from django.test import Client, TestCase, TransactionTestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from apps.academics.models import Faculty, Section, Student, Subject, TeachingAssignment
from apps.accounts.models import Role, User
from apps.attendance.calculations import student_attendance_summary
from apps.attendance.models import AttendanceRecord, AttendanceSession, AttendanceThreshold, Status
from apps.audit.models import AuditEntry
from apps.backups import storage
from apps.backups.models import Backup
from apps.notifications.models import Notification, ShortageFlag, WeeklyShortageEmail
from apps.notifications.services import send_weekly_faculty_emails

from .support_integration import PASSWORD, TEST_SETTINGS, IntegrationSupport, csv_rows, pdf_content_streams

P, A = Status.PRESENT, Status.ABSENT


@override_settings(**(TEST_SETTINGS | {"OTP_REQUIRED": True}))
class ProvisionedAttendanceJourneyTests(IntegrationSupport, TestCase):
    def test_provisioned_accounts_complete_otp_then_corrected_totals_agree_everywhere(self):
        """IT_01/02/03/05/06/07/08/09/34: UI provisioning through corrected exports."""
        admin = User.objects.create_user(
            username="JOURNEY_ADMIN", password=PASSWORD, role=Role.ADMIN, email="admin@example.test"
        )
        admin_client, admin_secret = self.first_otp_login(admin)
        self.assertEqual(admin_client.get(reverse("dashboard_admin")).status_code, 200)
        self.assertEqual(
            admin_client.post(
                reverse("section_create"), {"class_name": "Journey CSE", "name": "A"}
            ).status_code,
            302,
        )
        section = Section.objects.get(class_name="Journey CSE", name="A")
        faculty_page = admin_client.post(
            reverse("faculty_create"),
            {
                "faculty_id": "JF001",
                "full_name": "Journey Teacher",
                "department": "CSE",
                "email": "teacher@example.test",
            },
        )
        self.assertEqual(faculty_page.context["delivery"].status, "sent")
        self.assertEqual(mail.outbox[-1].to, ["teacher@example.test"])
        faculty_password = mail.outbox[-1].body.split("Temporary password: ")[1].splitlines()[0]
        faculty = Faculty.objects.get(faculty_id="JF001")
        student_page = admin_client.post(
            reverse("student_create"),
            {
                "roll_number": "JS001",
                "full_name": "Journey Student",
                "class_name": section.class_name,
                "home_section": section.pk,
                "email": "student@example.test",
            },
        )
        self.assertEqual(student_page.context["delivery"].status, "sent")
        self.assertEqual(mail.outbox[-1].to, ["student@example.test"])
        student_password = mail.outbox[-1].body.split("Temporary password: ")[1].splitlines()[0]
        student = Student.objects.get(roll_number="JS001")
        self.assertNotContains(student_page, student_password)
        self.assertTrue(student.user.check_password(student_password))
        self.assertNotEqual(student.user.password, student_password)

        assignments = []
        for code, name in (("JCS101", "Journey Programming"), ("JMA101", "Journey Mathematics")):
            self.assertEqual(
                admin_client.post(reverse("subject_create"), {"code": code, "name": name}).status_code, 302
            )
            subject = Subject.objects.get(code=code)
            self.assertEqual(
                admin_client.post(
                    reverse("class_assign", args=[section.pk]), {"subject": subject.pk, "faculty": faculty.pk}
                ).status_code,
                302,
            )
            assignment = TeachingAssignment.objects.get(section=section, subject=subject)
            self.assertEqual(
                admin_client.post(
                    reverse("enrollment_create", args=[section.pk]),
                    {"student": student.pk, "assignment": assignment.pk},
                ).status_code,
                302,
            )
            assignments.append(assignment)
        faculty_client, faculty_secret = self.first_otp_login(
            faculty.user, password=faculty_password, change_password=True
        )
        for period, status in enumerate((P, A, P), start=1):
            self.mark(faculty_client, assignments[0], period, {student.pk: status})
        self.mark(faculty_client, assignments[1], 4, {student.pk: P})
        student_client, student_secret = self.first_otp_login(
            student.user, password=student_password, change_password=True
        )
        summary_page = student_client.get(reverse("attendance_summary"))
        self.assertEqual(summary_page.context["summary"].overall.display, "3/4 (75.00%)")
        self.assertContains(summary_page, "2/3 (66.67%)")
        before = csv_rows(
            faculty_client.get(reverse("attendance_report_csv"), {"assignment": assignments[0].pk})
        )
        self.assertEqual(
            (before[0]["Classes Held"], before[0]["Present"], before[0]["Attendance Percentage"]),
            ("3", "2", "66.67"),
        )

        record = AttendanceRecord.objects.get(student=student, session__assignment=assignments[0], status=A)
        self.correct(faculty_client, record, P)
        corrected = student_client.get(reverse("attendance_summary"))
        dashboard = student_client.get(reverse("dashboard_student"))
        self.assertEqual(corrected.context["summary"].overall.display, "4/4 (100.00%)")
        self.assertEqual(dashboard.context["summary"].overall.display, "4/4 (100.00%)")
        self.assertFalse(dashboard.context["overall_below_threshold"])
        report = faculty_client.get(reverse("attendance_report"))
        self.assertEqual(report.context["overall"].display, "4/4 (100.00%)")
        csv_response = admin_client.get(reverse("attendance_report_csv"))
        rows = csv_rows(csv_response)
        self.assertEqual({row["Subject Code"] for row in rows}, {"JCS101", "JMA101"})
        self.assertTrue(all(row["Attendance Percentage"] == "100.00" for row in rows))
        pdf_response = admin_client.get(reverse("attendance_report_pdf"))
        self.assertEqual(pdf_response["Content-Type"], "application/pdf")
        self.assertTrue(pdf_response.content.startswith(b"%PDF-"))
        self.assertTrue(pdf_response.content.rstrip().endswith(b"%%EOF"))
        text = pdf_content_streams(pdf_response)
        for expected in (b"JS001", b"JCS101", b"JMA101", b"100.00%"):
            self.assertIn(expected, text)
        change = AuditEntry.objects.get(action="attendance.correct", target_id=str(record.pk))
        self.assertEqual((change.old_value, change.new_value), ({"status": A}, {"status": P}))
        self.assertEqual(change.actor_username, "JF001")
        self.assertFalse(change.is_admin_override)
        self.assertContains(
            faculty_client.get(reverse("attendance_changes", args=[record.pk])),
            "Verified against the class register",
        )
        self.assertEqual(AuditEntry.objects.filter(action="attendance.mark").count(), 4)
        audit_text = str(list(AuditEntry.objects.values("old_value", "new_value", "reason")))
        for secret in (admin_secret, faculty_secret, student_secret, faculty_password, student_password):
            self.assertNotIn(secret, audit_text)
        self.assertEqual(student_client.post(reverse("logout")).status_code, 302)
        self.assertEqual(student_client.get(reverse("attendance_summary")).status_code, 302)

    def test_password_only_session_cannot_bypass_otp_via_reports_or_post_requests(self):
        user = User.objects.create_user(
            username="OTP_STUDENT", password=PASSWORD, role=Role.STUDENT, email="otp@example.test"
        )
        Student.objects.create(user=user, roll_number=user.username, full_name="OTP Student")
        complete, _ = self.first_otp_login(user)
        complete.post(reverse("logout"))
        pending = self.sign_in(user)
        for name in ("dashboard_student", "attendance_summary", "attendance_report_csv", "backup_list"):
            with self.subTest(name=name):
                self.assertRedirects(pending.get(reverse(name)), reverse("otp_verify"))
        self.assertRedirects(pending.post(reverse("attendance_mark"), {}), reverse("otp_verify"))
        self.assertFalse(AttendanceSession.objects.exists())
        self.assertEqual(pending.post(reverse("otp_email")).status_code, 302)
        self.assertEqual(mail.outbox[-1].to, [user.email])
        code = re.search(r"\b(\d{6})\b", mail.outbox[-1].body).group(1)
        self.assertRedirects(
            pending.post(reverse("otp_verify"), {"code": code}),
            reverse("dashboard"),
            fetch_redirect_response=False,
        )
        self.assertEqual(pending.get(reverse("dashboard_student")).status_code, 200)


@override_settings(**TEST_SETTINGS)
class AttendanceAlertAndReportIntegrationTests(IntegrationSupport, TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.make_fixture()

    def test_threshold_alert_recovers_then_notifies_only_on_the_next_crossing(self):
        """IT_06/07/08/10: saved marks, corrections, flags, inbox and local email agree."""
        student, classmate, _ = self.students
        faculty = self.sign_in(self.faculty_user)
        self.mark(faculty, self.assignment, 1, {student.pk: P, classmate.pk: P})
        self.assertFalse(Notification.objects.exists())
        self.mark(faculty, self.assignment, 2, {student.pk: A, classmate.pk: P})
        self.assertEqual(Notification.objects.filter(recipient=student.user).count(), 1)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, [student.user.email])
        self.assertIn("1/2 (50.00%)", mail.outbox[0].body)
        self.mark(faculty, self.assignment, 3, {student.pk: A, classmate.pk: P})
        self.mark(faculty, self.assignment, 3, {student.pk: A, classmate.pk: P})
        self.assertEqual(AttendanceSession.objects.count(), 3)
        self.assertEqual(Notification.objects.count(), 1)
        self.assertEqual(len(mail.outbox), 1)
        absent = list(AttendanceRecord.objects.filter(student=student, status=A).order_by("session__period"))
        for record in absent:
            self.correct(faculty, record, P)
        self.assertFalse(ShortageFlag.objects.filter(student=student).exists())
        self.assertEqual(student_attendance_summary(student).overall.display, "3/3 (100.00%)")
        self.correct(faculty, absent[0], A)
        self.assertEqual(Notification.objects.filter(recipient=student.user).count(), 2)
        self.assertEqual(len(mail.outbox), 2)
        self.assertIn("2/3 (66.67%)", mail.outbox[-1].body)
        student_client = self.sign_in(student.user)
        self.assertContains(student_client.get(reverse("notification_list")), "2/3 (66.67%)")
        self.assertEqual(
            student_client.get(reverse("attendance_summary")).context["summary"].overall.display,
            "2/3 (66.67%)",
        )
        self.assertTrue(student_client.get(reverse("dashboard_student")).context["overall_below_threshold"])
        self.assertEqual(faculty.get(reverse("dashboard_faculty")).context["subject_shortages"], 1)
        self.assertEqual(
            self.sign_in(self.admin).get(reverse("dashboard_admin")).context["students_below_overall"], 1
        )

    def test_notification_email_failure_keeps_saved_attendance_and_private_inbox(self):
        student, classmate, _ = self.students
        with patch(
            "apps.notifications.services.send_mail", side_effect=SMTPException("Synthetic transport failure")
        ):
            self.mark(self.sign_in(self.faculty_user), self.assignment, 1, {student.pk: A, classmate.pk: P})
        self.assertEqual(student_attendance_summary(student).overall.display, "0/1 (0.00%)")
        self.assertEqual(Notification.objects.filter(recipient=student.user).count(), 1)
        self.assertEqual(len(mail.outbox), 0)
        self.assertTrue(AuditEntry.objects.filter(action="notification.email_failed").exists())
        self.assertContains(self.sign_in(student.user).get(reverse("notification_list")), "0/1 (0.00%)")
        self.assertNotContains(self.sign_in(classmate.user).get(reverse("notification_list")), "0/1 (0.00%)")

    def test_weekly_faculty_email_contains_only_their_class_and_is_not_resent(self):
        first, second, foreign = self.students
        self.mark(self.sign_in(self.faculty_user), self.assignment, 1, {first.pk: A, second.pk: P})
        self.mark(self.sign_in(self.other_faculty_user), self.other_assignment, 1, {foreign.pk: A})
        mail.outbox.clear()
        monday = datetime(2026, 11, 2, 8, tzinfo=ZoneInfo("Asia/Kolkata"))
        result = send_weekly_faculty_emails(now=monday)
        self.assertEqual(result["sent"], 2)
        messages = {message.to[0]: message.body for message in mail.outbox}
        self.assertIn(first.roll_number, messages[self.faculty_user.email])
        self.assertNotIn(foreign.roll_number, messages[self.faculty_user.email])
        self.assertIn(foreign.roll_number, messages[self.other_faculty_user.email])
        self.assertNotIn(first.roll_number, messages[self.other_faculty_user.email])
        self.assertEqual(send_weekly_faculty_emails(now=monday)["already_sent"], 2)
        self.assertEqual(len(mail.outbox), 2)
        self.assertEqual(WeeklyShortageEmail.objects.count(), 2)

    def test_failed_attendance_audit_rolls_back_roster_alerts_and_email(self):
        first, second, _ = self.students
        faculty = self.sign_in(self.faculty_user)
        with patch(
            "apps.attendance.services.audit.record", side_effect=IntegrityError("Synthetic audit failure")
        ):
            with self.committed_callbacks():
                response = faculty.post(
                    reverse("attendance_mark"),
                    self.marking_payload(self.assignment, 1, {first.pk: A, second.pk: P}),
                )
        self.assertEqual(response.status_code, 400)
        self.assertFalse(AttendanceSession.objects.exists())
        self.assertFalse(AttendanceRecord.objects.exists())
        self.assertFalse(Notification.objects.exists())
        self.assertFalse(ShortageFlag.objects.exists())
        self.assertEqual(len(mail.outbox), 0)

    def test_status_and_student_report_filters_preserve_the_real_denominator(self):
        first, second, _ = self.students
        faculty = self.sign_in(self.faculty_user)
        for period, status in enumerate((P, A, P), start=1):
            self.mark(faculty, self.assignment, period, {first.pk: status, second.pk: P})
        params = {"assignment": self.assignment.pk, "student": first.pk, "status": A}
        report = faculty.get(reverse("attendance_report"), params)
        self.assertEqual(report.context["overall"].display, "2/3 (66.67%)")
        rows = csv_rows(faculty.get(reverse("attendance_report_csv"), params))
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["Roll Number"], first.roll_number)
        self.assertEqual(
            (
                rows[0]["Classes Held"],
                rows[0]["Present"],
                rows[0]["Absent"],
                rows[0]["Attendance Percentage"],
            ),
            ("3", "2", "1", "66.67"),
        )
        pdf = faculty.get(reverse("attendance_report_pdf"), params)
        text = pdf_content_streams(pdf)
        self.assertIn(first.roll_number.encode(), text)
        self.assertIn(b"66.67%", text)
        self.assertNotIn(second.roll_number.encode(), text)

    def test_csv_formula_prefixes_are_escaped_without_changing_numeric_cells(self):
        first, second, _ = self.students
        faculty = self.sign_in(self.faculty_user)
        self.mark(faculty, self.assignment, 1, {first.pk: P, second.pk: A})
        for name in ("=1+1", "+SUM(1,2)", "-1+2", "@SUM(1,2)", "\t=1+1", "\r=1+1", "  =1+1"):
            with self.subTest(name=name):
                Student.objects.filter(pk=first.pk).update(full_name=name)
                rows = csv_rows(faculty.get(reverse("attendance_report_csv"), {"student": first.pk}))
                self.assertEqual(rows[0]["Student Name"], "'" + name)
                self.assertEqual(
                    (rows[0]["Classes Held"], rows[0]["Present"], rows[0]["Attendance Percentage"]),
                    ("1", "1", "100.00"),
                )
        Section.objects.filter(pk=self.section.pk).update(class_name="=CLASS()", name="@SECTION")
        Subject.objects.filter(pk=self.subject.pk).update(code="+CODE", name="-SUBJECT")
        row = csv_rows(faculty.get(reverse("attendance_report_csv"), {"student": first.pk}))[0]
        self.assertEqual(
            (row["Class"], row["Section"], row["Subject Code"], row["Subject Name"]),
            ("'=CLASS()", "'@SECTION", "'+CODE", "'-SUBJECT"),
        )

    def test_exports_are_private_audited_and_invalid_or_empty_exports_are_not_downloads(self):
        first, second, _ = self.students
        faculty = self.sign_in(self.faculty_user)
        self.mark(faculty, self.assignment, 1, {first.pk: P, second.pk: A})
        self.assertIn("no-store", faculty.get(reverse("attendance_report"))["Cache-Control"])
        for format_name in ("csv", "pdf"):
            with self.subTest(format=format_name):
                url = reverse(f"attendance_report_{format_name}")
                response = faculty.get(url, {"assignment": self.assignment.pk})
                self.assertEqual(response.status_code, 200)
                self.assertIn("no-store", response["Cache-Control"])
                self.assertIn("attachment", response["Content-Disposition"])
                event = AuditEntry.objects.filter(
                    action="reports.export", actor_username=self.faculty_user.username
                ).latest("pk")
                self.assertEqual(event.target_type, "AttendanceReport")
                self.assertEqual(event.new_value["format"], format_name)
                self.assertEqual(event.new_value["rows"], 2)
                invalid = faculty.get(url, {"start_date": "2026-10-25", "end_date": "2026-10-01"})
                self.assertEqual(invalid.status_code, 400)
                self.assertTrue(invalid["Content-Type"].startswith("text/html"))
                self.assertNotIn("Content-Disposition", invalid)
                empty = faculty.get(
                    url, {"start_date": (timezone.localdate() + timedelta(days=1)).isoformat()}
                )
                self.assertEqual(empty.status_code, 200)
                self.assertTrue(empty["Content-Type"].startswith("text/html"))
                self.assertNotIn("Content-Disposition", empty)
                self.assertContains(empty, "No attendance records match")
        self.assertEqual(AuditEntry.objects.filter(action="reports.export").count(), 2)


@override_settings(**TEST_SETTINGS)
class AuthorizationIntegrationTests(IntegrationSupport, TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.make_fixture()

    def setUp(self):
        first, second, foreign = self.students
        self.mark(self.sign_in(self.faculty_user), self.assignment, 1, {first.pk: P, second.pk: A})
        self.mark(self.sign_in(self.other_faculty_user), self.other_assignment, 1, {foreign.pk: A})

    def test_student_cannot_open_admin_faculty_or_another_students_resources(self):
        first, second, _ = self.students
        student = self.sign_in(first.user)
        own_record = AttendanceRecord.objects.get(student=first)
        endpoints = [
            ("account_list", []),
            ("student_create", []),
            ("faculty_create", []),
            ("attendance_history", []),
            ("attendance_report", []),
            ("attendance_report_csv", []),
            ("attendance_report_pdf", []),
            ("attendance_changes", [own_record.pk]),
            ("attendance_correct", [own_record.pk]),
            ("student_detail", [second.pk]),
            ("backup_list", []),
            ("correction_window_settings", []),
            ("threshold_settings", []),
            ("shortage_list", []),
        ]
        for name, args in endpoints:
            with self.subTest(endpoint=name):
                response = student.get(reverse(name, args=args))
                self.assertEqual(response.status_code, 403)
                self.assertNotIn("Content-Disposition", response)
        self.assertGreaterEqual(
            AuditEntry.objects.filter(action="access.denied", actor_username=first.user.username).count(),
            len(endpoints),
        )
        summary = student.get(reverse("attendance_summary"), {"student": second.pk, "user": second.user_id})
        self.assertEqual(summary.context["student"].pk, first.pk)
        self.assertEqual(summary.context["summary"].overall.display, "1/1 (100.00%)")
        self.assertNotContains(summary, second.roll_number)
        inbox = student.get(reverse("notification_list"), {"recipient": second.user_id})
        self.assertEqual(inbox.context["page_obj"].paginator.count, 0)
        self.assertNotContains(inbox, "0/1 (0.00%)")

    def test_faculty_cannot_read_export_or_modify_another_class(self):
        foreign = self.students[2]
        faculty = self.sign_in(self.faculty_user)
        foreign_record = AttendanceRecord.objects.get(student=foreign)
        requests = [
            ("get", "attendance_changes", [foreign_record.pk], {}),
            ("post", "attendance_correct", [foreign_record.pk], {"status": P, "reason": "forged"}),
            ("get", "attendance_history", [], {"assignment": self.other_assignment.pk}),
            ("get", "attendance_report", [], {"assignment": self.other_assignment.pk}),
            ("get", "attendance_report_csv", [], {"assignment": self.other_assignment.pk}),
            ("get", "attendance_report_pdf", [], {"student": foreign.pk}),
            ("post", "attendance_mark", [], self.marking_payload(self.other_assignment, 2, {foreign.pk: P})),
            ("post", "student_deactivate", [foreign.pk], {}),
            ("post", "account_resend_credentials", [foreign.user_id], {}),
            ("post", "backup_create", [], {}),
            ("post", "backup_restore", [uuid4()], {"password": PASSWORD, "confirm": "on"}),
        ]
        before = (AttendanceRecord.objects.count(), AttendanceSession.objects.count(), len(mail.outbox))
        for method, name, args, values in requests:
            with self.subTest(endpoint=name):
                response = getattr(faculty, method)(reverse(name, args=args), values)
                self.assertEqual(response.status_code, 403)
                self.assertNotIn("Content-Disposition", response)
                self.assertNotContains(response, foreign.roll_number, status_code=403)
        foreign_record.refresh_from_db()
        foreign.user.refresh_from_db()
        self.assertEqual(foreign_record.status, A)
        self.assertTrue(foreign.user.is_active)
        self.assertEqual(
            (AttendanceRecord.objects.count(), AttendanceSession.objects.count(), len(mail.outbox)), before
        )
        self.assertFalse(Backup.objects.exists())
        self.assertFalse(
            AuditEntry.objects.filter(
                action="reports.export", actor_username=self.faculty_user.username
            ).exists()
        )
        response = faculty.get(reverse("attendance_report_csv"))
        self.assertEqual(
            {row["Roll Number"] for row in csv_rows(response)},
            {self.students[0].roll_number, self.students[1].roll_number},
        )

    def test_mutating_endpoints_require_csrf_after_a_real_password_login(self):
        guarded = Client(enforce_csrf_checks=True)
        login_page = guarded.get(reverse("login"))
        self.assertEqual(login_page.status_code, 200)
        csrf = guarded.cookies["csrftoken"].value
        refused = guarded.post(reverse("login"), {"username": self.admin.username, "password": PASSWORD})
        self.assertEqual(refused.status_code, 403)
        response = guarded.post(
            reverse("login"),
            {"username": self.admin.username, "password": PASSWORD, "csrfmiddlewaretoken": csrf},
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn("_auth_user_id", guarded.session)
        before = (AttendanceSession.objects.count(), AttendanceRecord.objects.count(), len(mail.outbox))
        record = AttendanceRecord.objects.first()
        for name, args in (
            ("attendance_correct", [record.pk]),
            ("backup_create", []),
            ("threshold_settings", []),
            ("account_reset_password", [self.students[0].user_id]),
        ):
            with self.subTest(endpoint=name):
                response = guarded.post(
                    reverse(name, args=args), {"status": P, "value": 40, "reason": "forged"}
                )
                self.assertEqual(response.status_code, 403)
        self.assertEqual(
            (AttendanceSession.objects.count(), AttendanceRecord.objects.count(), len(mail.outbox)), before
        )
        self.assertFalse(Backup.objects.exists())


@override_settings(**TEST_SETTINGS)
class BackupRecoveryIntegrationTests(IntegrationSupport, TransactionTestCase):
    """IT_13: actual encrypted artifacts, committed restoration and rollback on PostgreSQL."""

    def setUp(self):
        self.make_fixture()
        folder = TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.backup_root = Path(folder.name) / "private-backups"
        self.test_key = Fernet.generate_key()
        config = override_settings(
            BACKUP_DIRECTORY=self.backup_root, BACKUP_ENCRYPTION_KEY=self.test_key.decode()
        )
        config.enable()
        self.addCleanup(config.disable)
        self.admin_client = self.sign_in(self.admin)
        first, second, _ = self.students
        self.mark(self.sign_in(self.faculty_user), self.assignment, 1, {first.pk: A, second.pk: P})
        self.first_record = AttendanceRecord.objects.get(student=first)

    def _fixture_teardown(self):
        # PostgreSQL blocks every application-side audit TRUNCATE. The test runner
        # alone disables this trigger while flushing its disposable database.
        with connection.cursor() as cursor:
            cursor.execute("ALTER TABLE audit_auditentry DISABLE TRIGGER audit_entry_no_truncate")
        try:
            super()._fixture_teardown()
        finally:
            with connection.cursor() as cursor:
                cursor.execute("ALTER TABLE audit_auditentry ENABLE TRIGGER audit_entry_no_truncate")

    def create_backup(self):
        response = self.admin_client.post(reverse("backup_create"))
        self.assertRedirects(response, reverse("backup_list"))
        backup = Backup.objects.get(kind=Backup.Kind.MANUAL)
        self.assertEqual(backup.status, Backup.Status.COMPLETE)
        return backup

    def test_encrypted_backup_restores_deleted_account_attendance_alerts_and_login(self):
        first = self.students[0]
        notification = Notification.objects.get(recipient=first.user)
        backup = self.create_backup()
        download = self.admin_client.get(reverse("backup_download", args=[backup.pk]))
        token = (self.backup_root / backup.filename).read_bytes()
        self.assertEqual(download.content, token)
        self.assertNotIn(first.roll_number.encode(), token)
        self.assertNotIn(first.user.email.encode(), token)
        self.assertNotIn(PASSWORD.encode(), token)
        self.assertEqual(storage.checksum(token), backup.checksum)
        self.assertIn("no-store", download["Cache-Control"])
        self.assertIn(b"attendance_attendancerecord", Fernet(self.test_key).decrypt(token))
        old_session = self.sign_in(first.user)
        session_key = old_session.session.session_key
        before_audit_ids = set(AuditEntry.objects.values_list("pk", flat=True))
        deleted = self.admin_client.post(
            reverse("student_delete", args=[first.pk]), {"reason": "Synthetic restore exercise"}
        )
        self.assertEqual(deleted.status_code, 302)
        self.assertFalse(Student.objects.filter(pk=first.pk).exists())
        self.assertFalse(AttendanceRecord.objects.filter(pk=self.first_record.pk).exists())
        mail_count = len(mail.outbox)
        response = self.admin_client.post(
            reverse("backup_restore", args=[backup.pk]), {"password": PASSWORD, "confirm": "on"}
        )
        self.assertRedirects(response, reverse("login"))
        restored = Student.objects.get(pk=first.pk)
        self.assertTrue(restored.user.check_password(PASSWORD))
        self.assertEqual(student_attendance_summary(restored).overall.display, "0/1 (0.00%)")
        self.assertEqual(Notification.objects.get(pk=notification.pk).recipient_id, restored.user_id)
        self.assertTrue(ShortageFlag.objects.filter(student=restored).exists())
        self.assertTrue(before_audit_ids.issubset(set(AuditEntry.objects.values_list("pk", flat=True))))
        self.assertTrue(AuditEntry.objects.filter(action="student.delete").exists())
        self.assertTrue(AuditEntry.objects.filter(action="restore.success").exists())
        self.assertEqual(
            Backup.objects.filter(kind=Backup.Kind.SAFETY, status=Backup.Status.COMPLETE).count(), 1
        )
        self.assertFalse(Session.objects.filter(session_key=session_key).exists())
        self.assertEqual(old_session.get(reverse("attendance_summary")).status_code, 302)
        self.assertEqual(len(mail.outbox), mail_count)
        student_client = self.sign_in(restored.user)
        self.assertContains(student_client.get(reverse("attendance_summary")), "0/1 (0.00%)")
        self.assertContains(student_client.get(reverse("notification_list")), "0/1 (0.00%)")

    def test_corrupted_artifact_is_refused_without_changing_live_corrections(self):
        backup = self.create_backup()
        self.correct(self.sign_in(self.faculty_user), self.first_record, P)
        path = self.backup_root / backup.filename
        with path.open("ab") as stream:
            stream.write(b"synthetic-corruption")
        response = self.admin_client.post(
            reverse("backup_restore", args=[backup.pk]), {"password": PASSWORD, "confirm": "on"}
        )
        self.assertContains(response, "checksum")
        self.first_record.refresh_from_db()
        self.assertEqual(self.first_record.status, P)
        self.assertEqual(student_attendance_summary(self.students[0]).overall.display, "1/1 (100.00%)")
        self.assertFalse(Backup.objects.filter(kind=Backup.Kind.SAFETY).exists())
        self.assertFalse(AuditEntry.objects.filter(action="restore.success").exists())
        self.assertTrue(AuditEntry.objects.filter(action="restore.failure").exists())

    def test_invalid_snapshot_relationship_rolls_back_all_live_modules(self):
        backup = self.create_backup()
        payload = storage.decrypt((self.backup_root / backup.filename).read_bytes())
        payload["tables"]["attendance_attendancerecord"][0]["student_id"] = 999999999
        invalid_token = storage.encrypt(payload)
        response = self.admin_client.post(
            reverse("backup_import"),
            {
                "backup_file": SimpleUploadedFile(
                    "invalid.backup", invalid_token, content_type="application/octet-stream"
                )
            },
        )
        self.assertRedirects(response, reverse("backup_list"))
        imported = Backup.objects.get(kind=Backup.Kind.IMPORTED)
        self.correct(self.sign_in(self.faculty_user), self.first_record, P)
        Student.objects.filter(pk=self.students[0].pk).update(full_name="Live corrected profile")
        AttendanceThreshold.objects.update_or_create(pk=1, defaults={"value": 80})
        notification_ids = set(Notification.objects.values_list("pk", flat=True))
        response = self.admin_client.post(
            reverse("backup_restore", args=[imported.pk]), {"password": PASSWORD, "confirm": "on"}
        )
        self.assertContains(response, "Current data is unchanged")
        self.first_record.refresh_from_db()
        self.assertEqual(self.first_record.status, P)
        self.assertEqual(Student.objects.get(pk=self.students[0].pk).full_name, "Live corrected profile")
        self.assertEqual(AttendanceThreshold.current_value(), 80)
        self.assertEqual(set(Notification.objects.values_list("pk", flat=True)), notification_ids)
        self.assertFalse(AuditEntry.objects.filter(action="restore.success").exists())
        self.assertTrue(AuditEntry.objects.filter(action="restore.failure").exists())
        self.assertEqual(
            Backup.objects.filter(kind=Backup.Kind.SAFETY, status=Backup.Status.COMPLETE).count(), 1
        )
