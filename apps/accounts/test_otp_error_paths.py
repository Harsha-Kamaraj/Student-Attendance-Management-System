"""Two-factor pages opened out of order, while locked, or during a concurrent change (Part 3 coverage)."""

from datetime import timedelta
from unittest.mock import patch

from django.urls import reverse
from django.utils import timezone

from . import otp
from .test_otp import OTPTestBase


class OTPPageOrderTests(OTPTestBase):
    def mark_verified(self):
        session = self.client.session
        session[otp.SESSION_VERIFIED] = True
        session.save()

    def test_code_pages_send_users_without_an_authenticator_to_setup(self):
        self.password_login("S001")
        self.assertRedirects(self.client.get(reverse("otp_verify")), reverse("otp_setup"))
        self.assertRedirects(self.client.post(reverse("otp_email")), reverse("otp_setup"))

    def test_already_verified_users_skip_the_code_pages(self):
        self.enroll(self.student)
        self.password_login("S001")
        self.mark_verified()
        self.assertRedirects(
            self.client.get(reverse("otp_verify")), reverse("dashboard"), fetch_redirect_response=False
        )
        self.assertRedirects(
            self.client.post(reverse("otp_email")), reverse("otp_verify"), target_status_code=302
        )

    def test_a_lock_that_starts_after_the_password_signs_the_user_out(self):
        self.enroll(self.student)
        self.password_login("S001")
        self.student.locked_until = timezone.now() + timedelta(minutes=15)
        self.student.save(update_fields=["locked_until"])
        response = self.client.get(reverse("otp_verify"))
        self.assertRedirects(response, reverse("login"))
        self.assertNotIn("_auth_user_id", self.client.session)


class OTPSetupRaceTests(OTPTestBase):
    """The account changes between opening the setup page and submitting the first code."""

    def start_setup(self):
        self.password_login("S001")
        self.client.get(reverse("otp_setup"))

    def test_lock_during_setup_signs_the_user_out(self):
        self.start_setup()
        with patch("apps.accounts.otp.confirm_setup", side_effect=otp.AccountLocked):
            response = self.client.post(reverse("otp_setup"), {"code": "123456"})
        self.assertRedirects(response, reverse("login"))
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_setup_finished_in_another_tab_goes_to_code_entry(self):
        self.start_setup()
        self.assertIn(otp.SESSION_SETUP_SECRET, self.client.session)
        with patch("apps.accounts.otp.confirm_setup", side_effect=otp.AlreadyConfigured):
            response = self.client.post(reverse("otp_setup"), {"code": "123456"})
        self.assertRedirects(response, reverse("otp_verify"), target_status_code=302)
        self.assertNotIn(otp.SESSION_SETUP_SECRET, self.client.session)
