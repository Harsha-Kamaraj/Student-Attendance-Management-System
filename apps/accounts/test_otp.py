"""BL-33: two-factor login with one-time codes (SEC-29 to SEC-32, UC-01 steps 3c, 4, 4a, 4b)."""

import os
import re
from datetime import UTC, datetime, timedelta
from smtplib import SMTPException
from unittest.mock import patch

import pyotp
from django.conf import settings
from django.core import mail
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from apps.audit.models import AuditEntry

from . import otp
from .models import OTPEmailCode, Role, User

PASSWORD = "Attend#2026"


def code_at(secret, steps_ahead=0):
    """Authenticator code for now, or for the next 30-second step (accepted for clock drift)."""
    return pyotp.TOTP(secret).at(timezone.now() + timedelta(seconds=30 * steps_ahead))


class OTPDefaultTests(TestCase):
    def test_otp_is_required_by_default(self):
        if os.environ.get("OTP_REQUIRED") is not None:
            self.skipTest("OTP_REQUIRED is set in this local environment")
        self.assertTrue(settings.OTP_REQUIRED_CONFIGURED)


@override_settings(OTP_REQUIRED=True, PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class OTPTestBase(TestCase):
    def setUp(self):
        clock = patch("apps.accounts.otp.timezone.now", return_value=datetime(2026, 10, 27, 12, tzinfo=UTC))
        clock.start()
        self.addCleanup(clock.stop)
        self.admin = User.objects.create_user(
            username="ADMIN1", password=PASSWORD, role=Role.ADMIN, email="a@x.edu"
        )
        self.faculty = User.objects.create_user(
            username="F001", password=PASSWORD, role=Role.FACULTY, email="f@x.edu"
        )
        self.student = User.objects.create_user(
            username="S001", password=PASSWORD, role=Role.STUDENT, email="s@x.edu"
        )

    def password_login(self, username, client=None):
        client = client or self.client
        client.post(reverse("login"), {"username": username, "password": PASSWORD})
        return client

    def enroll(self, user):
        """Give a user a confirmed authenticator; returns (secret, backup codes)."""
        secret = otp.new_secret()
        codes = otp.confirm_setup(user, secret, code_at(secret))
        user.refresh_from_db()
        return secret, codes

    def submit(self, code, client=None):
        return (client or self.client).post(reverse("otp_verify"), {"code": code})


class PasswordAloneTests(OTPTestBase):
    def test_password_alone_does_not_reach_a_dashboard(self):
        # SEC-29, UT_01_5
        self.enroll(self.student)
        self.password_login("S001")
        for url in (reverse("dashboard"), reverse("dashboard_student"), reverse("attendance_summary")):
            with self.subTest(url=url):
                self.assertRedirects(self.client.get(url), reverse("otp_verify"))

    def test_django_admin_is_also_blocked_until_the_code(self):
        root = User.objects.create_superuser(username="root", password=PASSWORD)
        self.enroll(root)
        self.client.post("/admin/login/", {"username": "root", "password": PASSWORD})
        self.assertRedirects(self.client.get("/admin/"), reverse("otp_verify"))

    def test_every_role_must_set_up_otp(self):
        # SEC-29, ST_01_7
        for username in ("ADMIN1", "F001", "S001"):
            with self.subTest(user=username):
                client = self.password_login(username, self.client_class())
                self.assertRedirects(client.get(reverse("dashboard")), reverse("otp_setup"))

    def test_logout_works_before_the_code_is_entered(self):
        self.password_login("S001")
        response = self.client.post(reverse("logout"))
        self.assertRedirects(response, reverse("login"))
        self.assertNotIn("_auth_user_id", self.client.session)


class SetupTests(OTPTestBase):
    def test_first_login_setup_flow(self):
        # UC-01 3c, SEC-30, ST_01_6
        self.password_login("S001")
        page = self.client.get(reverse("otp_setup"))
        self.assertContains(page, "<svg")
        self.assertContains(page, "Can't scan?")
        secret = self.client.session[otp.SESSION_SETUP_SECRET]
        self.assertEqual(self.client.get(reverse("otp_setup")).context["manual_key"].replace(" ", ""), secret)

        wrong = self.client.post(reverse("otp_setup"), {"code": "not-a-code"})
        self.assertContains(wrong, "That code is not right")
        self.student.refresh_from_db()
        self.assertFalse(self.student.otp_confirmed)

        done = self.client.post(reverse("otp_setup"), {"code": code_at(secret)})
        listed = done.content.decode().split('data-testid="backup-codes"')[1].split("</ul>")[0]
        codes = re.findall(r">([a-z0-9]{4}-[a-z0-9]{4})<", listed)
        self.assertEqual(len(codes), 10)
        self.assertIn("no-store", done["Cache-Control"])
        self.student.refresh_from_db()
        self.assertTrue(self.student.otp_confirmed)
        self.assertEqual(self.client.get(reverse("dashboard_student")).status_code, 200)

    def test_setup_page_is_not_shown_again_after_setup(self):
        self.enroll(self.student)
        self.password_login("S001")
        self.assertRedirects(self.client.get(reverse("otp_setup")), reverse("otp_verify"))

    def test_secret_never_appears_in_the_audit_log_or_emails(self):
        # SEC-30, IT_01_5
        secret, _ = self.enroll(self.student)
        self.password_login("S001")
        self.client.post(reverse("otp_email"))
        logged = " ".join(str(e.__dict__) for e in AuditEntry.objects.all())
        self.assertNotIn(secret, logged)
        self.assertTrue(all(secret not in m.body for m in mail.outbox))
        self.assertTrue(AuditEntry.objects.filter(action="otp.setup", actor_username="S001").exists())

    def test_first_login_with_temporary_password_sets_up_otp_then_changes_password(self):
        # SEC-06 and SEC-30 together
        self.student.must_change_password = True
        self.student.save()
        self.password_login("S001")
        self.assertRedirects(self.client.get(reverse("dashboard")), reverse("otp_setup"))
        secret = self.client.session[otp.SESSION_SETUP_SECRET]
        self.client.post(reverse("otp_setup"), {"code": code_at(secret)})
        self.assertRedirects(self.client.get(reverse("dashboard")), reverse("password_change"))


class AuthenticatorCodeTests(OTPTestBase):
    def test_correct_code_completes_login(self):
        secret, _ = self.enroll(self.student)
        self.password_login("S001")
        self.assertRedirects(
            self.submit(code_at(secret, 1)), reverse("dashboard"), fetch_redirect_response=False
        )
        self.assertEqual(self.client.get(reverse("dashboard_student")).status_code, 200)
        entry = AuditEntry.objects.filter(action="otp.success").last()
        self.assertEqual(entry.new_value, {"method": "authenticator"})

    def test_a_code_cannot_be_reused(self):
        secret, _ = self.enroll(self.student)
        code = code_at(secret, 1)
        self.password_login("S001")
        self.submit(code)
        other = self.password_login("S001", self.client_class())
        response = self.submit(code, other)
        self.assertContains(response, "That code is not right or has already been used.")

    def test_session_id_changes_when_login_completes(self):
        secret, _ = self.enroll(self.student)
        self.password_login("S001")
        before = self.client.session.session_key
        self.submit(code_at(secret, 1))
        self.assertNotEqual(self.client.session.session_key, before)

    def test_no_remember_this_device(self):
        # ST_01_7: every login asks again
        secret, _ = self.enroll(self.student)
        self.password_login("S001")
        self.submit(code_at(secret, 1))
        self.client.post(reverse("logout"))
        self.password_login("S001")
        self.assertRedirects(self.client.get(reverse("dashboard")), reverse("otp_verify"))


class LockoutTests(OTPTestBase):
    def test_five_wrong_codes_lock_the_account(self):
        # SEC-32, UT_01_6
        secret, _ = self.enroll(self.student)
        self.password_login("S001")
        for _ in range(4):
            self.assertContains(self.submit("not-a-code"), "That code is not right")
        response = self.submit("not-a-code", None)
        self.assertRedirects(response, reverse("login"), fetch_redirect_response=False)
        self.assertNotIn("_auth_user_id", self.client.session)
        self.student.refresh_from_db()
        self.assertGreater(self.student.locked_until, timezone.now() + timedelta(minutes=14))

        # Even the right password is refused while locked.
        self.password_login("S001")
        self.assertNotIn("_auth_user_id", self.client.session)
        actions = list(AuditEntry.objects.filter(action__startswith="otp.f").values_list("action", flat=True))
        self.assertEqual(actions, ["otp.failure"] * 5)
        self.assertTrue(AuditEntry.objects.filter(action="otp.lockout").exists())

    def test_logging_in_again_does_not_reset_the_wrong_code_count(self):
        self.enroll(self.student)
        self.password_login("S001")
        for _ in range(4):
            self.submit("not-a-code")
        self.client.post(reverse("logout"))
        self.password_login("S001")
        self.submit("not-a-code")
        self.student.refresh_from_db()
        self.assertIsNotNone(self.student.locked_until)

    def test_correct_code_resets_the_count(self):
        secret, _ = self.enroll(self.student)
        self.password_login("S001")
        for _ in range(4):
            self.submit("not-a-code")
        self.submit(code_at(secret, 1))
        self.student.refresh_from_db()
        self.assertEqual(self.student.otp_failed_count, 0)


class BackupCodeTests(OTPTestBase):
    def test_backup_code_works_once(self):
        # SEC-31, UT_01_8
        _, codes = self.enroll(self.student)
        self.password_login("S001")
        self.assertRedirects(self.submit(codes[0]), reverse("dashboard"), fetch_redirect_response=False)
        self.assertEqual(otp.remaining_backup_codes(self.student), 9)
        other = self.password_login("S001", self.client_class())
        self.assertContains(self.submit(codes[0], other), "That code is not right")

    def test_backup_codes_are_stored_only_as_hashes(self):
        _, codes = self.enroll(self.student)
        stored = list(self.student.otp_backup_codes.values_list("code_hash", flat=True))
        self.assertEqual(len(stored), 10)
        for code in codes:
            self.assertFalse(any(code.replace("-", "") in h for h in stored))

    def test_backup_code_typed_without_dash_or_in_capitals_is_accepted(self):
        _, codes = self.enroll(self.student)
        self.password_login("S001")
        response = self.submit(codes[1].replace("-", " ").upper())
        self.assertRedirects(response, reverse("dashboard"), fetch_redirect_response=False)


class EmailCodeTests(OTPTestBase):
    def setUp(self):
        super().setUp()
        self.enroll(self.student)
        self.password_login("S001")

    def emailed_code(self, index=-1):
        return re.search(r"\b(\d{6})\b", mail.outbox[index].body).group(1)

    def test_emailed_code_is_sent_only_to_the_user_and_works_once(self):
        # SEC-32, UT_01_7
        response = self.client.post(reverse("otp_email"), follow=True)
        self.assertContains(response, "A code was sent to s***@x.edu")
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["s@x.edu"])
        code = self.emailed_code()
        self.assertRedirects(self.submit(code), reverse("dashboard"), fetch_redirect_response=False)
        other = self.password_login("S001", self.client_class())
        self.assertContains(self.submit(code, other), "That code is not right")

    def test_emailed_code_expires_after_10_minutes(self):
        self.client.post(reverse("otp_email"))
        OTPEmailCode.objects.update(expires_at=timezone.now() - timedelta(seconds=1))
        self.assertContains(self.submit(self.emailed_code()), "That code is not right")

    def test_at_most_3_emailed_codes_in_15_minutes(self):
        for _ in range(3):
            self.client.post(reverse("otp_email"))
        response = self.client.post(reverse("otp_email"), follow=True)
        self.assertContains(response, "at most 3 email codes in 15 minutes")
        self.assertEqual(len(mail.outbox), 3)
        self.assertTrue(AuditEntry.objects.filter(action="otp.email_refused").exists())

    def test_account_without_email_is_told_to_use_a_backup_code(self):
        self.faculty.email = ""
        self.faculty.save()
        self.enroll(self.faculty)
        client = self.password_login("F001", self.client_class())
        response = client.post(reverse("otp_email"), follow=True)
        self.assertContains(response, "no email address")
        self.assertNotContains(client.get(reverse("otp_verify")), "Email me a code")


class AdminResetTests(OTPTestBase):
    def setUp(self):
        super().setUp()
        admin_secret, _ = self.enroll(self.admin)
        self.password_login("ADMIN1")
        self.submit(code_at(admin_secret, 1))
        self.enroll(self.faculty)
        self.url = reverse("account_reset_otp", args=[self.faculty.pk])

    def test_reset_needs_the_admins_password(self):
        # SEC-31, IT_01_4
        response = self.client.post(self.url, {"password": "Wrong#2026"})
        self.assertContains(response, "Incorrect password.")
        self.faculty.refresh_from_db()
        self.assertTrue(self.faculty.otp_confirmed)

    def test_admin_password_reauthentication_is_rate_limited(self):
        for _ in range(5):
            self.client.post(self.url, {"password": "Wrong#2026"})
        response = self.client.post(self.url, {"password": PASSWORD})
        self.assertContains(response, "Incorrect password.")
        self.faculty.refresh_from_db()
        self.assertTrue(self.faculty.otp_confirmed)
        self.admin.refresh_from_db()
        self.assertTrue(otp.is_locked(self.admin))

    def test_reset_clears_otp_and_forces_setup_again(self):
        response = self.client.post(self.url, {"password": PASSWORD})
        self.assertRedirects(response, reverse("account_list"), fetch_redirect_response=False)
        self.faculty.refresh_from_db()
        self.assertFalse(self.faculty.otp_confirmed)
        self.assertEqual(self.faculty.otp_secret, "")
        self.assertEqual(self.faculty.otp_backup_codes.count(), 0)
        self.assertTrue(AuditEntry.objects.filter(action="otp.reset", actor_username="ADMIN1").exists())
        client = self.password_login("F001", self.client_class())
        self.assertRedirects(client.get(reverse("dashboard")), reverse("otp_setup"))

    def test_account_list_shows_status_and_reset_button(self):
        page = self.client.get(reverse("account_list"))
        self.assertContains(page, "Two-factor")
        self.assertContains(page, self.url)

    def test_admin_cannot_reset_their_own_otp_here(self):
        response = self.client.post(
            reverse("account_reset_otp", args=[self.admin.pk]), {"password": PASSWORD}
        )
        self.assertEqual(response.status_code, 403)


class OTPSecurityTests(OTPTestBase):
    def test_five_failed_setup_codes_lock_across_sessions(self):
        self.password_login("S001")
        for _ in range(4):
            self.client.post(reverse("otp_setup"), {"code": "wrong"})
        other = self.password_login("S001", self.client_class())
        response = other.post(reverse("otp_setup"), {"code": "wrong"})
        self.assertRedirects(response, reverse("login"), fetch_redirect_response=False)
        # A session opened before the lockout cannot finish setup either.
        secret = self.client.session[otp.SESSION_SETUP_SECRET]
        self.client.post(reverse("otp_setup"), {"code": code_at(secret)})
        self.assertNotIn("_auth_user_id", self.client.session)
        self.student.refresh_from_db()
        self.assertFalse(self.student.otp_confirmed)
        self.assertTrue(otp.is_locked(self.student))
        self.assertEqual(AuditEntry.objects.filter(action="otp.setup_failure").count(), 5)
        self.assertEqual(AuditEntry.objects.filter(action="otp.lockout").count(), 1)

    def test_unicode_codes_are_rejected_without_server_errors(self):
        self.password_login("S001")
        response = self.client.post(reverse("otp_setup"), {"code": "１２３４５６"})
        self.assertContains(response, "That code is not right")
        self.enroll(self.student)
        self.assertContains(self.submit("１２３４５６"), "That code is not right")

    def test_stale_setup_cannot_replace_an_existing_authenticator(self):
        stale_user = User.objects.get(pk=self.student.pk)
        secret, _ = self.enroll(self.student)
        second_secret = otp.new_secret()
        with self.assertRaises(otp.AlreadyConfigured):
            otp.confirm_setup(stale_user, second_secret, code_at(second_secret))
        self.student.refresh_from_db()
        self.assertEqual(self.student.otp_secret, secret)

    def test_locked_account_cannot_verify_even_with_stale_user_object(self):
        secret, codes = self.enroll(self.student)
        User.objects.filter(pk=self.student.pk).update(locked_until=timezone.now() + timedelta(minutes=15))
        self.assertEqual(otp.verify_code(self.student, code_at(secret, 1)), (False, True))
        self.assertEqual(otp.verify_code(self.student, codes[0]), (False, True))
        self.assertEqual(otp.remaining_backup_codes(self.student), 10)

    def test_login_works_after_lockout_expires(self):
        secret, _ = self.enroll(self.student)
        self.student.locked_until = timezone.now() - timedelta(seconds=1)
        self.student.save()
        self.password_login("S001")
        self.submit(code_at(secret, 1))
        self.assertEqual(self.client.get(reverse("dashboard_student")).status_code, 200)

    def test_reset_invalidates_verified_and_pending_sessions(self):
        secret, codes = self.enroll(self.student)
        self.password_login("S001")
        self.submit(code_at(secret, 1))
        pending = self.password_login("S001", self.client_class())
        otp.send_email_code(self.student)
        otp.reset_otp(user=self.student, reset_by=self.admin)
        for client in (self.client, pending):
            response = client.get(reverse("dashboard_student"))
            self.assertTrue(response.url.startswith(reverse("login")))
            self.assertNotIn("_auth_user_id", client.session)
        self.assertFalse(self.student.otp_email_codes.exists())
        self.assertFalse(otp.verify_code(self.student, codes[0])[0])
        self.password_login("S001")
        self.assertRedirects(self.client.get(reverse("dashboard_student")), reverse("otp_setup"))

    def test_reset_invalidates_pending_setup_secrets(self):
        self.password_login("S001")
        self.client.get(reverse("otp_setup"))
        secret = self.client.session[otp.SESSION_SETUP_SECRET]
        otp.reset_otp(user=self.student, reset_by=self.admin)
        response = self.client.post(reverse("otp_setup"), {"code": code_at(secret)})
        self.assertTrue(response.url.startswith(reverse("login")))
        self.student.refresh_from_db()
        self.assertFalse(self.student.otp_confirmed)

    def test_django_admin_repeat_password_login_requires_a_fresh_code(self):
        root = User.objects.create_superuser(username="ROOT", password=PASSWORD)
        secret, _ = self.enroll(root)
        self.password_login("ROOT")
        self.submit(code_at(secret, 1))
        self.assertTrue(self.client.session[otp.SESSION_VERIFIED])
        self.client.post("/admin/login/", {"username": "ROOT", "password": PASSWORD})
        self.assertNotIn(otp.SESSION_VERIFIED, self.client.session)
        self.assertRedirects(self.client.get("/admin/"), reverse("otp_verify"))

    def test_setup_verify_and_email_posts_require_csrf(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.student)
        for name in ("otp_setup", "otp_verify", "otp_email"):
            with self.subTest(name=name):
                self.assertEqual(client.post(reverse(name), {"code": "123456"}).status_code, 403)

    def test_otp_pages_are_not_cached(self):
        self.password_login("S001")
        self.assertIn("no-store", self.client.get(reverse("otp_setup"))["Cache-Control"])
        self.enroll(self.student)
        self.assertIn("no-store", self.client.get(reverse("otp_verify"))["Cache-Control"])

    def test_email_failure_is_recoverable_and_does_not_leak_secrets(self):
        self.enroll(self.student)
        self.password_login("S001")
        with patch("apps.accounts.otp.send_mail", side_effect=SMTPException("private server detail")):
            response = self.client.post(reverse("otp_email"), follow=True)
        self.assertContains(response, "Email could not be sent")
        self.assertNotContains(response, "private server detail")
        self.assertIsNotNone(self.student.otp_email_codes.get().used_at)
        self.assertTrue(AuditEntry.objects.filter(action="otp.email_failed").exists())

    def test_email_get_and_locked_session_cannot_send_codes(self):
        self.enroll(self.student)
        self.password_login("S001")
        self.assertEqual(self.client.get(reverse("otp_email")).status_code, 405)
        User.objects.filter(pk=self.student.pk).update(locked_until=timezone.now() + timedelta(minutes=15))
        self.client.post(reverse("otp_email"))
        self.assertFalse(self.student.otp_email_codes.exists())
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_email_limit_recovers_after_15_minutes(self):
        self.enroll(self.student)
        for _ in range(3):
            otp.send_email_code(self.student)
        with self.assertRaises(otp.TooManyEmailCodes):
            otp.send_email_code(self.student)
        self.student.otp_email_codes.update(created_at=timezone.now() - timedelta(minutes=16))
        otp.send_email_code(self.student)
        self.assertEqual(len(mail.outbox), 4)

    def test_faculty_cannot_reset_otp(self):
        faculty_secret, _ = self.enroll(self.faculty)
        client = self.password_login("F001", self.client_class())
        self.submit(code_at(faculty_secret, 1), client)
        response = client.post(reverse("account_reset_otp", args=[self.student.pk]), {"password": PASSWORD})
        self.assertEqual(response.status_code, 403)
