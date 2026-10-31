"""BL-34 / #42: private credential delivery, recovery and Admin-only resends."""

import html
from io import StringIO
from unittest.mock import patch

from django.core import mail
from django.core.exceptions import PermissionDenied
from django.core.mail import get_connection
from django.db import IntegrityError
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from apps.academics.models import Faculty, Section, Student
from apps.audit.models import AuditEntry

from .credentials import deliver_login_details
from .models import Role, User
from .services import provision_account, reset_password

PASSWORD = "Attend#2026"


@override_settings(
    SITE_URL="https://attendance.example.edu",
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"],
    OTP_REQUIRED=False,
)
class CredentialEmailTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            username="ADMIN", role=Role.ADMIN, password=PASSWORD, email="admin@example.edu"
        )
        self.section = Section.objects.create(class_name="CSE", name="A")
        self.client.force_login(self.admin)

    def student(self, **overrides):
        return self.client.post(
            reverse("student_create"),
            {
                "roll_number": "S042",
                "full_name": "Private Student Name",
                "class_name": "CSE",
                "home_section": self.section.pk,
                "email": "student@example.edu",
                **overrides,
            },
        )

    def faculty(self):
        return self.client.post(
            reverse("faculty_create"),
            {
                "faculty_id": "F042",
                "full_name": "Private Faculty Name",
                "department": "SECRETDEPT",
                "email": "faculty@example.edu",
            },
        )

    def email_password(self):
        return mail.outbox[-1].body.split("Temporary password: ")[1].splitlines()[0]

    def fallback_password(self, response):
        return html.unescape(
            response.content.decode().split('data-testid="temporary-password">')[1].split("<")[0]
        )

    def assert_private(self, user, response):
        message = mail.outbox[-1]
        password = self.email_password()
        self.assertEqual(message.recipients(), [user.email])
        self.assertEqual(message.cc, [])
        self.assertEqual(message.bcc, [])
        self.assertIn(f"Username: {user.username}", message.body)
        self.assertIn("Login: https://attendance.example.edu/login/", message.body)
        self.assertIn("must change it at first login", message.body)
        for private in ("Private Student Name", "Private Faculty Name", "SECRETDEPT", self.admin.email):
            self.assertNotIn(private, message.body)
        self.assertTrue(user.check_password(password))
        self.assertTrue(user.must_change_password)
        self.assertNotContains(response, password)
        self.assertNotContains(response, 'data-testid="temporary-password"')
        self.assertNotContains(response, user.email)
        self.assertIn("no-store", response["Cache-Control"])
        self.assertNotIn(password, str(dict(self.client.session)))
        self.assertNotIn(password, str(list(AuditEntry.objects.values())))
        self.assertNotIn(password, user.password)
        self.assertTrue(
            AuditEntry.objects.filter(action="credentials.email_sent", target_id=str(user.pk)).exists()
        )

    def test_student_creation_emails_only_owner_and_hides_successful_password(self):
        response = self.student()
        self.assert_private(Student.objects.get(roll_number="S042").user, response)
        self.assertEqual(len(mail.outbox), 1)
        self.assertContains(response, "Login details sent to s***@example.edu")

    def test_faculty_creation_emails_only_owner(self):
        response = self.faculty()
        self.assert_private(Faculty.objects.get(faculty_id="F042").user, response)

    def test_reset_and_resend_rotate_password_and_audit_purpose(self):
        self.student()
        user = User.objects.get(username="S042")
        first = self.email_password()
        for route, purpose in (("account_reset_password", "reset"), ("account_resend_credentials", "resend")):
            response = self.client.post(reverse(route, args=[user.pk]))
            user.refresh_from_db()
            self.assert_private(user, response)
            self.assertFalse(user.check_password(first))
            first = self.email_password()
            self.assertTrue(
                AuditEntry.objects.filter(
                    action="credentials.email_sent", new_value__purpose=purpose
                ).exists()
            )
        self.assertEqual(len(mail.outbox), 3)

    def test_email_failure_keeps_account_and_shows_password_only_in_original_response(self):
        # Include a password and provider secret in the exception to ensure neither is recorded.
        temporary = "Ab3&<x>Yz9!q"
        with (
            patch("apps.accounts.services.generate_temporary_password", return_value=temporary),
            patch(
                "apps.accounts.credentials.EmailMessage.send",
                side_effect=RuntimeError(f"{temporary} SMTP_SECRET"),
            ),
        ):
            with self.assertNoLogs("apps.accounts", level="WARNING"):
                response = self.student()
        user = User.objects.get(username="S042")
        self.assertEqual(self.fallback_password(response), temporary)
        self.assertTrue(user.check_password(temporary))
        self.assertContains(response, "could not be emailed")
        self.assertNotContains(response, "SMTP_SECRET")
        log = str(list(AuditEntry.objects.values()))
        self.assertNotIn(temporary, log)
        self.assertNotIn("SMTP_SECRET", log)
        self.assertTrue(AuditEntry.objects.filter(action="credentials.email_failed").exists())
        self.assertNotIn(temporary, str(dict(self.client.session)))
        self.assertNotContains(self.client.get(reverse("student_create")), temporary)
        self.assertNotContains(self.client.get(reverse("account_list")), temporary)
        retry = self.client.post(reverse("account_resend_credentials", args=[user.pk]))
        user.refresh_from_db()
        self.assert_private(user, retry)
        self.assertFalse(user.check_password(temporary))

    def test_zero_messages_sent_is_failure_and_returns_fallback_on_reset(self):
        self.student()
        user = User.objects.get(username="S042")
        with patch("apps.accounts.credentials.EmailMessage.send", return_value=0):
            response = self.client.post(reverse("account_reset_password", args=[user.pk]))
        user.refresh_from_db()
        self.assertTrue(user.check_password(self.fallback_password(response)))
        self.assertContains(response, "could not be emailed")

    def test_missing_email_and_inactive_recipient_use_fallback_without_sending(self):
        for active, email in ((True, ""), (False, "inactive@example.edu")):
            user = User.objects.create_user(
                username=f"USER{active}", role=Role.STUDENT, is_active=active, email=email
            )
            response = self.client.post(reverse("account_reset_password", args=[user.pk]))
            user.refresh_from_db()
            self.assertTrue(user.check_password(self.fallback_password(response)))
        self.assertEqual(len(mail.outbox), 0)

    def test_failed_profile_transaction_never_sends_email(self):
        for route, model in ((self.student, Student), (self.faculty, Faculty)):
            with patch.object(model.objects, "create", side_effect=IntegrityError("test rollback")):
                response = route()
            self.assertEqual(response.status_code, 200)
        self.assertEqual(len(mail.outbox), 0)
        self.assertFalse(User.objects.filter(username__in=["S042", "F042"]).exists())
        self.assertFalse(AuditEntry.objects.filter(action="account.create").exists())

    def test_invalid_and_duplicate_submissions_do_not_email(self):
        self.student(email="invalid")
        self.assertEqual(len(mail.outbox), 0)
        self.student()
        self.student()
        self.assertEqual(len(mail.outbox), 1)

    def test_resend_after_password_change_is_rejected_without_reset(self):
        self.student()
        user = User.objects.get(username="S042")
        user.set_password(PASSWORD)
        user.must_change_password = False
        user.save()
        response = self.client.post(reverse("account_resend_credentials", args=[user.pk]))
        self.assertRedirects(response, reverse("account_list"))
        user.refresh_from_db()
        self.assertTrue(user.check_password(PASSWORD))
        self.assertEqual(len(mail.outbox), 1)

    def test_non_admins_cannot_trigger_creation_reset_resend_or_delivery_service(self):
        target, temporary = provision_account(
            username="TARGET", role=Role.STUDENT, email="target@example.edu", created_by=self.admin
        )
        for role in (Role.FACULTY, Role.STUDENT):
            actor = User.objects.create_user(username=role, role=role, password=PASSWORD)
            self.client.force_login(actor)
            for name, args in (
                ("student_create", []),
                ("faculty_create", []),
                ("account_reset_password", [target.pk]),
                ("account_resend_credentials", [target.pk]),
            ):
                self.assertEqual(self.client.post(reverse(name, args=args)).status_code, 403)
            with self.assertRaises(PermissionDenied):
                deliver_login_details(
                    user=target, temporary_password=temporary, actor=actor, purpose="resend"
                )
            with self.assertRaises(PermissionDenied):
                reset_password(user=target, reset_by=actor)
        self.assertEqual(len(mail.outbox), 0)

    def test_resend_requires_post_and_csrf(self):
        self.student()
        user = User.objects.get(username="S042")
        url = reverse("account_resend_credentials", args=[user.pk])
        self.assertEqual(self.client.get(url).status_code, 405)
        secure = Client(enforce_csrf_checks=True)
        secure.force_login(self.admin)
        self.assertEqual(secure.post(url).status_code, 403)
        self.assertEqual(len(mail.outbox), 1)

    def test_email_uses_configured_origin_not_request_host(self):
        with override_settings(ALLOWED_HOSTS=["untrusted.example"]):
            response = self.client.post(
                reverse("faculty_create"),
                {"faculty_id": "F042", "full_name": "Faculty", "department": "CSE", "email": "f@example.edu"},
                HTTP_HOST="untrusted.example",
            )
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("untrusted.example", mail.outbox[0].body)
        self.assertIn("https://attendance.example.edu/login/", mail.outbox[0].body)

    def test_invalid_or_non_https_production_origin_falls_back(self):
        for index, url in enumerate(
            (
                "",
                "http://attendance.example.edu",
                "https://user:pass@example.edu",
                "https://example.edu/?x=1",
            )
        ):
            with self.subTest(url=url), override_settings(SITE_URL=url, DEBUG=False):
                response = self.student(roll_number=f"S{index}")
                self.assertContains(response, "could not be emailed")
                self.assertTrue(self.fallback_password(response))
        self.assertEqual(len(mail.outbox), 0)

    def test_stale_password_is_not_sent_or_shown(self):
        self.student()
        user = User.objects.get(username="S042")
        stale = self.email_password()
        reset_password(user=user, reset_by=self.admin)
        result = deliver_login_details(user=user, temporary_password=stale, actor=self.admin, purpose="reset")
        self.assertEqual(result.status, "superseded")
        self.assertEqual(len(mail.outbox), 1)

    def test_development_console_preview_is_not_claimed_as_delivered(self):
        output = StringIO()
        connection = get_connection("django.core.mail.backends.console.EmailBackend", stream=output)
        with (
            override_settings(DEBUG=True, EMAIL_BACKEND="django.core.mail.backends.console.EmailBackend"),
            patch("django.core.mail.get_connection", return_value=connection),
        ):
            response = self.student()
        self.assertContains(response, "No email was delivered")
        self.assertNotContains(response, 'data-testid="temporary-password"')
        self.assertIn("Temporary password:", output.getvalue())
        self.assertTrue(AuditEntry.objects.filter(action="credentials.email_preview").exists())

    def test_production_console_and_file_storage_are_refused(self):
        for index, backend in enumerate(("console", "filebased", "dummy")):
            with override_settings(
                DEBUG=False, EMAIL_BACKEND=f"django.core.mail.backends.{backend}.EmailBackend"
            ):
                with patch("apps.accounts.credentials.EmailMessage.send") as send:
                    response = self.student(roll_number=f"S{index}")
                send.assert_not_called()
                self.assertTrue(self.fallback_password(response))

    def test_emailed_password_still_requires_first_login_change(self):
        self.student()
        self.client.logout()
        self.client.post(reverse("login"), {"username": "S042", "password": self.email_password()})
        self.assertRedirects(self.client.get(reverse("dashboard")), reverse("password_change"))
