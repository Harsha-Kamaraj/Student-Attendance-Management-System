"""Forgotten-password requests to the Admin and the login lockout warning."""

from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse

from apps.audit.models import AuditEntry

from .models import Role, User
from .services import reset_password

PASSWORD = "Attend#2026"


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend", OTP_REQUIRED=False)
class ForgotPasswordTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            username="ADMIN1", password=PASSWORD, role=Role.ADMIN, email="admin@example.edu"
        )
        self.student = User.objects.create_user(
            username="S001", password=PASSWORD, role=Role.STUDENT, email="s001@example.edu"
        )

    def ask(self, username):
        return self.client.post(reverse("forgot_password"), {"username": username})

    def test_login_page_links_to_forgot_password(self):
        self.assertContains(self.client.get(reverse("login")), reverse("forgot_password"))

    def test_request_flags_account_and_emails_admins(self):
        response = self.ask("s001")
        self.assertContains(response, "the Admin has been asked to reset its password")
        self.student.refresh_from_db()
        self.assertIsNotNone(self.student.password_reset_requested_at)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["admin@example.edu"])
        self.assertIn("S001", mail.outbox[0].subject)
        self.assertNotIn("s001@example.edu", mail.outbox[0].body)
        self.assertTrue(AuditEntry.objects.filter(action="password.reset_requested").exists())

        self.client.force_login(self.admin)
        self.assertContains(self.client.get(reverse("account_list")), "Reset requested")
        self.assertContains(self.client.get(reverse("dashboard_admin")), "1</strong> password reset request")

    def test_unknown_and_known_usernames_get_the_same_reply(self):
        known, unknown = self.ask("S001"), self.ask("NOBODY")
        self.assertEqual(known.status_code, unknown.status_code)
        self.assertEqual(known.content, unknown.content)
        self.assertEqual(len(mail.outbox), 1)  # only the real account notified the Admin

    def test_repeat_request_within_15_minutes_sends_no_more_email(self):
        self.ask("S001")
        self.ask("S001")
        self.assertEqual(len(mail.outbox), 1)

    def test_admin_reset_clears_the_request(self):
        self.ask("S001")
        reset_password(user=self.student, reset_by=self.admin)
        self.student.refresh_from_db()
        self.assertIsNone(self.student.password_reset_requested_at)

    def test_signed_in_users_are_sent_to_their_dashboard(self):
        self.client.force_login(self.student)
        self.assertRedirects(
            self.client.get(reverse("forgot_password")), reverse("dashboard"), fetch_redirect_response=False
        )


@override_settings(OTP_REQUIRED=False)
class LoginLockoutWarningTests(TestCase):
    def setUp(self):
        User.objects.create_user(username="S001", password=PASSWORD, role=Role.STUDENT)

    def fail(self, username):
        return self.client.post(reverse("login"), {"username": username, "password": "Wrong#2026x"})

    def test_fifth_failure_warns_about_the_pause_for_real_and_unknown_accounts(self):
        for username in ("S001", "NOBODY"):
            with self.subTest(username=username):
                self.client = self.client_class()
                for _ in range(4):
                    response = self.fail(username)
                    self.assertContains(response, "Invalid username or password.")
                response = self.fail(username)
                self.assertContains(response, "paused for 15 minutes")
                self.assertNotContains(response, "Invalid username or password.")

    def test_successful_login_clears_the_counter(self):
        for _ in range(3):
            self.fail("S001")
        self.client.post(reverse("login"), {"username": "S001", "password": PASSWORD})
        self.assertNotIn("login_failure_times", self.client.session)
