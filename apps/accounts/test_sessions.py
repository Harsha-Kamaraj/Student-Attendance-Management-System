"""BL-06 / UC-12: logout and inactivity timeout regressions."""

from datetime import timedelta

from django.conf import settings
from django.contrib.sessions.models import Session
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from apps.audit.models import AuditEntry

from .models import Role, User

PASSWORD = "Attend#2026"


class LogoutAndSessionTests(TestCase):
    def setUp(self):
        self.student = User.objects.create_user(username="21CS001", password=PASSWORD, role=Role.STUDENT)

    def sign_in(self):
        response = self.client.post(reverse("login"), {"username": "21CS001", "password": PASSWORD})
        self.assertRedirects(response, reverse("dashboard"), fetch_redirect_response=False)
        self.assertIn("_auth_user_id", self.client.session)

    def test_logout_invalidates_session_and_returns_to_login(self):
        # UT_12_1 / IT_12_1: Logout flushes the server-side session.
        self.sign_in()
        previous_key = self.client.session.session_key

        response = self.client.post(reverse("logout"))

        self.assertRedirects(response, reverse("login"))
        self.assertNotIn("_auth_user_id", self.client.session)
        self.assertFalse(Session.objects.filter(session_key=previous_key).exists())
        self.assertTrue(AuditEntry.objects.filter(action="logout", actor_username="21CS001").exists())

    def test_protected_pages_reject_previous_session_after_logout(self):
        # ST_12_1: Even a revisited protected URL requires a fresh login.
        self.sign_in()
        self.client.post(reverse("logout"))

        dashboard_url = reverse("dashboard_student")
        response = self.client.get(dashboard_url)
        self.assertRedirects(response, f"{reverse('login')}?next={dashboard_url}")
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_logout_only_accepts_post(self):
        self.sign_in()
        response = self.client.get(reverse("logout"))
        self.assertEqual(response.status_code, 405)
        self.assertIn("_auth_user_id", self.client.session)

    def test_logout_form_appears_on_signed_in_page(self):
        self.sign_in()
        response = self.client.get(reverse("dashboard_student"))
        self.assertContains(response, f'action="{reverse("logout")}"')
        self.assertContains(response, "Log out")
        self.assertIn("no-store", response["Cache-Control"])

    def test_missing_csrf_token_cannot_log_out(self):
        csrf_client = Client(enforce_csrf_checks=True)
        csrf_client.force_login(self.student)
        response = csrf_client.post(reverse("logout"))
        self.assertEqual(response.status_code, 403)
        self.assertIn("_auth_user_id", csrf_client.session)

    def test_first_login_user_can_log_out_without_changing_password(self):
        self.student.must_change_password = True
        self.student.save(update_fields=["must_change_password"])
        self.sign_in()
        response = self.client.post(reverse("logout"))
        self.assertRedirects(response, reverse("login"))
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_session_expires_after_inactivity_and_relogin_works(self):
        # IT_12_2 / ST_12_2: Simulate inactivity by expiring stored session.
        self.sign_in()
        session_key = self.client.session.session_key
        Session.objects.filter(session_key=session_key).update(
            expire_date=timezone.now() - timedelta(seconds=1)
        )

        dashboard_url = reverse("dashboard_student")
        response = self.client.get(dashboard_url)
        self.assertRedirects(response, f"{reverse('login')}?next={dashboard_url}")
        self.assertNotIn("_auth_user_id", self.client.session)

        self.sign_in()
        response = self.client.get(dashboard_url)
        self.assertEqual(response.status_code, 200)

    def test_inactivity_policy_is_15_minutes_and_sliding(self):
        self.assertEqual(settings.SESSION_COOKIE_AGE, 15 * 60)
        self.assertTrue(settings.SESSION_SAVE_EVERY_REQUEST)
