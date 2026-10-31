"""Synthetic fixtures and output readers shared by the BL-31 integration journeys."""

import base64
import csv
import re
import zlib
from contextlib import nullcontext
from io import StringIO

import pyotp
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from apps.academics.models import Enrollment, Faculty, Section, Student, Subject, TeachingAssignment
from apps.accounts import otp
from apps.accounts.models import Role, User

PASSWORD = "Attend#2026"
NEW_PASSWORD = "Replaced#9362"
TEST_SETTINGS = {
    "OTP_REQUIRED": False,
    "EMAIL_BACKEND": "django.core.mail.backends.locmem.EmailBackend",
    "DEFAULT_FROM_EMAIL": "attendance@example.test",
    "SITE_URL": "https://attendance.example.test",
}


def csv_rows(response):
    return list(csv.DictReader(StringIO(response.content.decode("utf-8-sig"))))


def pdf_content_streams(response):
    """Read ReportLab's text-bearing streams using only the standard library.

    This is an output assertion helper, not a general PDF parser or a layout
    check. ReportLab emits ASCII85/Flate streams with these filters.
    """
    streams = []
    for match in re.finditer(rb"<<(.*?)>>\s*stream\r?\n(.*?)endstream", response.content, re.DOTALL):
        metadata, content = match.groups()
        content = content.strip()
        if b"/ASCII85Decode" in metadata:
            content = base64.a85decode(content, adobe=True)
        if b"/FlateDecode" in metadata:
            content = zlib.decompress(content)
        streams.append(content)
    return b"\n".join(streams)


class IntegrationSupport:
    def report_params(self, **filters):
        today = timezone.localdate().isoformat()
        return {"start_date": today, "end_date": today, "all_records": "on", **filters}

    def committed_callbacks(self):
        # TestCase holds an outer transaction; TransactionTestCase commits naturally.
        if hasattr(self, "captureOnCommitCallbacks"):
            return self.captureOnCommitCallbacks(execute=True)
        return nullcontext()

    def sign_in(self, user, *, password=PASSWORD, client=None):
        client = client or Client()
        response = client.post(reverse("login"), {"username": user.username, "password": password})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(str(client.session.get("_auth_user_id")), str(user.pk))
        return client

    def first_otp_login(self, user, *, password=PASSWORD, change_password=False):
        client = self.sign_in(user, password=password)
        self.assertRedirects(client.get(reverse("dashboard")), reverse("otp_setup"))
        self.assertEqual(client.get(reverse("otp_setup")).status_code, 200)
        secret = client.session[otp.SESSION_SETUP_SECRET]
        response = client.post(reverse("otp_setup"), {"code": pyotp.TOTP(secret).at(timezone.now())})
        self.assertContains(response, "backup-codes")
        self.assertTrue(client.session[otp.SESSION_VERIFIED])
        if change_password:
            self.assertRedirects(client.get(reverse("dashboard")), reverse("password_change"))
            response = client.post(
                reverse("password_change"),
                {"old_password": password, "new_password1": NEW_PASSWORD, "new_password2": NEW_PASSWORD},
            )
            self.assertRedirects(response, reverse("dashboard"), fetch_redirect_response=False)
            user.refresh_from_db()
            self.assertFalse(user.must_change_password)
            self.assertTrue(user.check_password(NEW_PASSWORD))
            self.assertFalse(user.check_password(password))
        return client, secret

    def marking_payload(self, assignment, period, statuses, day=None):
        return {
            "assignment": assignment.pk,
            "date": (day or timezone.localdate()).isoformat(),
            "period": period,
            **{f"status_{student_id}": status for student_id, status in statuses.items()},
        }

    def mark(self, client, assignment, period, statuses):
        with self.committed_callbacks():
            response = client.post(
                reverse("attendance_mark"), self.marking_payload(assignment, period, statuses)
            )
        self.assertEqual(response.status_code, 302, response.content[:500])
        return response

    def correct(self, client, record, status, *, reason="Verified against the class register"):
        with self.committed_callbacks():
            response = client.post(
                reverse("attendance_correct", args=[record.pk]), {"status": status, "reason": reason}
            )
        self.assertRedirects(
            response, reverse("attendance_changes", args=[record.pk]), fetch_redirect_response=False
        )
        return response

    @classmethod
    def make_fixture(cls):
        cls.admin = User.objects.create_user(
            username="INTEGRATION_ADMIN", password=PASSWORD, role=Role.ADMIN, email="admin@example.test"
        )
        cls.faculty_user = User.objects.create_user(
            username="INTEGRATION_F1", password=PASSWORD, role=Role.FACULTY, email="f1@example.test"
        )
        cls.other_faculty_user = User.objects.create_user(
            username="INTEGRATION_F2", password=PASSWORD, role=Role.FACULTY, email="f2@example.test"
        )
        faculty = Faculty.objects.create(
            user=cls.faculty_user,
            faculty_id="INTEGRATION_F1",
            full_name="Synthetic Teacher One",
            department="CSE",
        )
        other_faculty = Faculty.objects.create(
            user=cls.other_faculty_user,
            faculty_id="INTEGRATION_F2",
            full_name="Synthetic Teacher Two",
            department="CSE",
        )
        cls.section = Section.objects.create(class_name="Integration CSE", name="A")
        cls.other_section = Section.objects.create(class_name="Integration CSE", name="B")
        cls.subject = Subject.objects.create(code="ITCS101", name="Integration Programming")
        cls.other_subject = Subject.objects.create(code="ITMA101", name="Integration Mathematics")
        cls.assignment = TeachingAssignment.objects.create(
            section=cls.section, subject=cls.subject, faculty=faculty
        )
        cls.other_assignment = TeachingAssignment.objects.create(
            section=cls.other_section, subject=cls.other_subject, faculty=other_faculty
        )
        cls.students = []
        for number, assignment in enumerate((cls.assignment, cls.assignment, cls.other_assignment), start=1):
            user = User.objects.create_user(
                username=f"ITS{number:03}",
                password=PASSWORD,
                role=Role.STUDENT,
                email=f"s{number}@example.test",
            )
            student = Student.objects.create(
                user=user, roll_number=user.username, full_name=f"Synthetic Student {number}"
            )
            Enrollment.objects.create(student=student, assignment=assignment)
            cls.students.append(student)
