"""The "Send these details by email" button under a temporary password."""

from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse

from apps.audit.models import AuditEntry

from .models import Role, User

PASSWORD = "Attend#2026"


@override_settings(
    SITE_URL="https://attendance.example.edu",
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"],
    OTP_REQUIRED=False,
)
class SendCredentialsTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(username="ADMIN1", role=Role.ADMIN, password=PASSWORD)
        self.teacher = User.objects.create_user(username="F002", role=Role.FACULTY, password=PASSWORD)
        self.client.force_login(self.admin)

    def reset(self):
        """Reset F002 (no email on the account) and return the temporary password shown."""
        response = self.client.post(reverse("account_reset_password", args=[self.teacher.pk]))
        self.assertContains(response, "Send these details by email")
        return response.context["temporary_password"]

    def send(self, temporary_password, email="f002@example.edu"):
        return self.client.post(
            reverse("account_send_credentials", args=[self.teacher.pk]),
            {"temporary_password": temporary_password, "purpose": "reset", "email": email},
        )

    def test_send_emails_the_details_and_saves_the_address(self):
        temporary_password = self.reset()
        self.assertEqual(len(mail.outbox), 0)  # no address yet, so nothing was sent on reset
        response = self.send(temporary_password)
        self.assertContains(response, "Login details sent to f***@example.edu")
        self.assertNotContains(response, temporary_password)  # not shown again once sent
        self.assertEqual(mail.outbox[-1].to, ["f002@example.edu"])
        self.assertIn("Username: F002", mail.outbox[-1].body)
        self.assertIn(f"Temporary password: {temporary_password}", mail.outbox[-1].body)
        self.teacher.refresh_from_db()
        self.assertEqual(self.teacher.email, "f002@example.edu")
        self.assertTrue(AuditEntry.objects.filter(action="account.email.update").exists())
        self.assertTrue(AuditEntry.objects.filter(action="credentials.email_sent").exists())

    def test_only_the_current_temporary_password_can_be_sent(self):
        self.reset()
        response = self.send("Not#TheRealOne1")
        self.assertRedirects(response, reverse("account_list"))
        self.assertEqual(len(mail.outbox), 0)
        self.teacher.refresh_from_db()
        self.assertEqual(self.teacher.email, "")

    def test_an_invalid_address_shows_the_form_again(self):
        temporary_password = self.reset()
        response = self.send(temporary_password, email="not-an-email")
        self.assertEqual(response.status_code, 400)
        self.assertContains(response, "Enter a valid email address.", status_code=400)
        self.assertContains(response, temporary_password, status_code=400)
        self.assertEqual(len(mail.outbox), 0)

    def test_only_the_admin_can_send_login_details(self):
        temporary_password = self.reset()
        # F002 now has a temporary password, so use another faculty member who can browse freely.
        other = User.objects.create_user(username="F003", role=Role.FACULTY, password=PASSWORD)
        self.client.force_login(other)
        self.assertEqual(self.send(temporary_password).status_code, 403)
        self.assertEqual(len(mail.outbox), 0)
