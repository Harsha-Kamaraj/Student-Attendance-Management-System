import html
from datetime import timedelta
from unittest import mock

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.audit.models import AuditEntry

from .models import Role, User
from .services import MAX_FAILED_LOGINS, generate_temporary_password, provision_account
from .validators import PasswordComplexityValidator

PASSWORD = "Attend#2026"
GENERIC_ERROR = "Invalid username or password."


def make_user(username, role, **extra):
    return User.objects.create_user(username=username, password=PASSWORD, role=role, **extra)


class UserModelTests(TestCase):
    def test_project_uses_custom_user_model(self):
        self.assertIs(get_user_model(), User)

    def test_password_is_stored_hashed(self):
        # SEC-05
        user = make_user("21CS001", Role.STUDENT)
        self.assertNotEqual(user.password, PASSWORD)
        self.assertTrue(user.password.startswith("pbkdf2_sha256$"))
        self.assertTrue(user.check_password(PASSWORD))

    def test_superuser_gets_admin_role(self):
        admin = User.objects.create_superuser(username="admin1", password=PASSWORD)
        self.assertEqual(admin.role, Role.ADMIN)

    def test_unknown_role_is_rejected(self):
        with transaction.atomic(), self.assertRaises(IntegrityError):
            make_user("x1", "GUEST")

    def test_missing_role_is_rejected(self):
        with transaction.atomic(), self.assertRaises(IntegrityError):
            User.objects.create_user(username="x2", password=PASSWORD)

    def test_usernames_are_stored_in_capitals(self):
        self.assertEqual(make_user(" 21cs001 ", Role.STUDENT).username, "21CS001")

    def test_username_is_unique_ignoring_case(self):
        make_user("21CS001", Role.STUDENT)
        with transaction.atomic(), self.assertRaises(IntegrityError):
            make_user("21cs001", Role.STUDENT)

    def test_lowercase_username_is_rejected_by_database(self):
        user = make_user("21CS001", Role.STUDENT)
        with transaction.atomic(), self.assertRaises(IntegrityError):
            User.objects.filter(pk=user.pk).update(username="21cs001")


class PasswordPolicyTests(TestCase):
    """SEC-04: at least 8 characters with upper, lower, digit and special character."""

    def test_weak_passwords_are_rejected(self):
        from django.contrib.auth.password_validation import validate_password

        for weak in ("Ab1!", "attend#2026", "ATTEND#2026", "Attendance#", "Attend2026"):
            with self.subTest(password=weak), self.assertRaises(ValidationError):
                validate_password(weak)

    def test_compliant_password_is_accepted(self):
        PasswordComplexityValidator().validate(PASSWORD)

    def test_temporary_passwords_meet_the_policy(self):
        from django.contrib.auth.password_validation import validate_password

        for _ in range(50):
            validate_password(generate_temporary_password())


class LoginTests(TestCase):
    def setUp(self):
        self.admin = make_user("ADMIN1", Role.ADMIN)
        self.faculty = make_user("F001", Role.FACULTY)
        self.student = make_user("21CS001", Role.STUDENT)

    def login(self, username, password=PASSWORD):
        return self.client.post(reverse("login"), {"username": username, "password": password}, follow=True)

    def test_each_role_reaches_its_dashboard(self):
        # UT_01_1, ST_01_1
        for username, url, heading in (
            ("ADMIN1", "dashboard_admin", "Admin dashboard"),
            ("F001", "dashboard_faculty", "Faculty dashboard"),
            ("21CS001", "dashboard_student", "Student dashboard"),
        ):
            with self.subTest(role=username):
                response = self.login(username)
                self.assertRedirects(response, reverse(url))
                self.assertContains(response, heading)
                self.client.logout()

    def test_login_ignores_username_case(self):
        response = self.login("21cs001")
        self.assertRedirects(response, reverse("dashboard_student"))

    def test_blank_fields_are_rejected(self):
        # UT_01_2
        response = self.client.post(reverse("login"), {"username": "", "password": ""})
        self.assertContains(response, "This field is required.", count=2)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_wrong_username_and_wrong_password_show_the_same_message(self):
        # UT_01_3, ST_01_2, SEC-02
        wrong_user = self.login("NOBODY")
        wrong_password = self.login("21CS001", "Wrong#2026")
        for response in (wrong_user, wrong_password):
            self.assertContains(response, GENERIC_ERROR)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_no_self_registration(self):
        # UT_01_4, BL-01 D-02
        self.assertEqual(self.client.get("/register/").status_code, 404)
        page = self.client.get(reverse("login")).content.decode().lower()
        self.assertNotIn("sign up", page)
        self.assertNotIn("register", page)

    def test_deactivated_account_cannot_log_in(self):
        # ST_01_3, UC-01 3b, SEC-15
        self.student.is_active = False
        self.student.save()
        response = self.login("21CS001")
        self.assertContains(response, "This account is deactivated. Contact the Admin.")
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_deactivated_account_with_wrong_password_gets_generic_message(self):
        self.student.is_active = False
        self.student.save()
        response = self.login("21CS001", "Wrong#2026")
        self.assertContains(response, GENERIC_ERROR)
        self.assertNotContains(response, "deactivated")

    def test_reactivated_account_can_log_in(self):
        # ST_01_4
        self.student.is_active = False
        self.student.save()
        self.student.is_active = True
        self.student.save()
        self.assertRedirects(self.login("21CS001"), reverse("dashboard_student"))

    def test_deactivating_ends_an_existing_session(self):
        # SEC-15
        self.login("21CS001")
        User.objects.filter(pk=self.student.pk).update(is_active=False)
        response = self.client.get(reverse("dashboard_student"))
        self.assertRedirects(response, f"{reverse('login')}?next={reverse('dashboard_student')}")

    def test_user_cannot_open_another_roles_dashboard(self):
        # IT_01_2
        self.login("21CS001")
        for url in ("dashboard_admin", "dashboard_faculty", "account_list", "account_create"):
            with self.subTest(url=url):
                self.assertEqual(self.client.get(reverse(url)).status_code, 403)

    def test_dashboard_requires_login(self):
        response = self.client.get(reverse("dashboard"))
        self.assertRedirects(response, f"{reverse('login')}?next={reverse('dashboard')}")


class LockoutTests(TestCase):
    """SEC-03: after 5 consecutive failures the account is locked for 15 minutes."""

    def setUp(self):
        self.student = make_user("21CS001", Role.STUDENT)

    def login(self, password):
        return self.client.post(reverse("login"), {"username": "21CS001", "password": password})

    def fail(self, times):
        for _ in range(times):
            self.login("Wrong#2026")

    def test_fifth_failure_locks_and_correct_password_is_then_rejected(self):
        self.fail(MAX_FAILED_LOGINS)
        self.student.refresh_from_db()
        self.assertIsNotNone(self.student.locked_until)
        response = self.login(PASSWORD)
        self.assertContains(response, GENERIC_ERROR)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_four_failures_do_not_lock(self):
        self.fail(MAX_FAILED_LOGINS - 1)
        self.login(PASSWORD)
        self.assertIn("_auth_user_id", self.client.session)

    def test_success_resets_the_failure_count(self):
        self.fail(MAX_FAILED_LOGINS - 1)
        self.login(PASSWORD)
        self.student.refresh_from_db()
        self.assertEqual(self.student.failed_login_count, 0)

    def test_login_works_again_after_15_minutes(self):
        self.fail(MAX_FAILED_LOGINS)
        User.objects.filter(pk=self.student.pk).update(locked_until=timezone.now() - timedelta(seconds=1))
        self.login(PASSWORD)
        self.assertIn("_auth_user_id", self.client.session)

    def test_lock_lasts_15_minutes(self):
        before = timezone.now()
        self.fail(MAX_FAILED_LOGINS)
        self.student.refresh_from_db()
        self.assertAlmostEqual((self.student.locked_until - before).total_seconds(), 15 * 60, delta=5)

    def test_every_failure_and_the_lockout_are_logged(self):
        self.fail(MAX_FAILED_LOGINS)
        self.login(PASSWORD)
        actions = list(AuditEntry.objects.order_by("id").values_list("action", flat=True))
        self.assertEqual(actions, ["login.failure"] * 4 + ["login.lockout", "login.locked"])

    def test_lockout_also_applies_to_the_django_admin_login(self):
        make_user("ADMIN2", Role.ADMIN, is_staff=True)
        admin_login = {"username": "ADMIN2", "password": PASSWORD}
        self.client.post("/admin/login/", admin_login)
        self.assertIn("_auth_user_id", self.client.session)  # works while not locked
        self.client.logout()

        for _ in range(MAX_FAILED_LOGINS):
            self.client.post(reverse("login"), {"username": "ADMIN2", "password": "Wrong#2026"})
        self.client.post("/admin/login/", admin_login)
        self.assertNotIn("_auth_user_id", self.client.session)


class AccountProvisioningTests(TestCase):
    def setUp(self):
        self.admin = make_user("ADMIN1", Role.ADMIN)
        self.client.login(username="ADMIN1", password=PASSWORD)

    def create(self, **data):
        values = {"username": "21cs050", "role": Role.STUDENT, "email": "s50@example.edu"} | data
        return self.client.post(reverse("account_create"), values)

    def temporary_password(self, response):
        raw = response.content.decode().split('data-testid="temporary-password">')[1].split("<")[0]
        return html.unescape(raw)  # what the Admin sees in the browser

    def test_admin_creates_account_with_temporary_password(self):
        # BL-01 D-02, AR-01
        response = self.create()
        self.assertEqual(response.status_code, 200)
        user = User.objects.get(username="21CS050")
        self.assertEqual(user.role, Role.STUDENT)
        self.assertTrue(user.must_change_password)
        temporary = self.temporary_password(response)
        self.assertTrue(user.check_password(temporary))
        self.assertNotIn(temporary, user.password)
        self.assertIn("no-store", response["Cache-Control"])

    def test_temporary_password_with_html_special_characters_is_shown_correctly(self):
        with mock.patch("apps.accounts.services.generate_temporary_password", return_value="Ab3&<x>Yz9!q"):
            response = self.create()
        self.assertEqual(self.temporary_password(response), "Ab3&<x>Yz9!q")
        self.assertTrue(User.objects.get(username="21CS050").check_password("Ab3&<x>Yz9!q"))

    def test_duplicate_username_is_rejected_ignoring_case(self):
        self.create()
        response = self.create(username="21CS050")
        self.assertContains(response, "An account with this username already exists.")
        self.assertEqual(User.objects.filter(username="21CS050").count(), 1)

    def test_blank_and_invalid_input_is_rejected(self):
        response = self.create(username="", email="not-an-email")
        self.assertContains(response, "This field is required.")
        self.assertContains(response, "Enter a valid email address.")
        self.assertFalse(User.objects.exclude(pk=self.admin.pk).exists())

    def test_account_creation_is_logged_without_the_password(self):
        # SEC-16, SEC-22
        response = self.create()
        temporary = self.temporary_password(response)
        entry = AuditEntry.objects.get(action="account.create")
        self.assertEqual(entry.actor_username, "ADMIN1")
        self.assertEqual(entry.new_value, {"username": "21CS050", "role": "STUDENT"})
        for logged in AuditEntry.objects.all():
            self.assertNotIn(temporary, str(logged.__dict__))

    def test_created_account_persists_after_relogin(self):
        # IT_01_3
        self.create()
        self.client.logout()
        self.client.login(username="ADMIN1", password=PASSWORD)
        self.assertContains(self.client.get(reverse("account_list")), "21CS050")

    def test_admin_can_reset_a_password(self):
        student = make_user("21CS051", Role.STUDENT, locked_until=timezone.now() + timedelta(minutes=10))
        response = self.client.post(reverse("account_reset_password", args=[student.pk]))
        temporary = self.temporary_password(response)
        student.refresh_from_db()
        self.assertTrue(student.check_password(temporary))
        self.assertTrue(student.must_change_password)
        self.assertIsNone(student.locked_until)
        self.assertTrue(AuditEntry.objects.filter(action="password.reset", actor_username="ADMIN1").exists())

    def test_reset_requires_post(self):
        student = make_user("21CS051", Role.STUDENT)
        self.assertEqual(
            self.client.get(reverse("account_reset_password", args=[student.pk])).status_code, 405
        )


class FirstLoginTests(TestCase):
    """ST_01_5, SEC-06: a temporary password must be changed before anything else."""

    def setUp(self):
        admin = make_user("ADMIN1", Role.ADMIN)
        self.user, self.temporary = provision_account(
            username="21CS060", role=Role.STUDENT, email="s60@example.edu", created_by=admin
        )

    def test_full_first_login_flow(self):
        response = self.client.post(
            reverse("login"), {"username": "21CS060", "password": self.temporary}, follow=True
        )
        self.assertRedirects(response, reverse("password_change"))
        self.assertContains(response, "You are using a temporary password.")

        for url in ("dashboard", "dashboard_student", "home"):
            with self.subTest(url=url):
                self.assertRedirects(self.client.get(reverse(url)), reverse("password_change"))

        weak = self.client.post(
            reverse("password_change"),
            {"old_password": self.temporary, "new_password1": "password", "new_password2": "password"},
        )
        self.assertEqual(weak.status_code, 200)
        self.user.refresh_from_db()
        self.assertTrue(self.user.must_change_password)

        response = self.client.post(
            reverse("password_change"),
            {
                "old_password": self.temporary,
                "new_password1": "New#Pass2026",
                "new_password2": "New#Pass2026",
            },
            follow=True,
        )
        self.assertRedirects(response, reverse("dashboard_student"))
        self.assertContains(response, "Your password has been changed.")
        self.user.refresh_from_db()
        self.assertFalse(self.user.must_change_password)
        self.assertTrue(
            AuditEntry.objects.filter(action="password.change", actor_username="21CS060").exists()
        )

        self.client.logout()
        self.assertTrue(self.client.login(username="21CS060", password="New#Pass2026"))
