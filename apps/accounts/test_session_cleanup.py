"""Stored login sessions end when an account is deactivated or deleted (D-03, D-04, SEC-15)."""

from datetime import timedelta

from django.contrib.auth import SESSION_KEY
from django.contrib.sessions.backends.db import SessionStore
from django.contrib.sessions.models import Session
from django.core.management import call_command
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from apps.academics.tests import make_faculty, make_student

from .models import Role, User
from .sessions import end_user_sessions

PASSWORD = "Attend#2026"


def sessions_of(user):
    return sum(1 for s in Session.objects.all() if s.get_decoded().get(SESSION_KEY) == str(user.pk))


class SessionCleanupTests(TestCase):
    def setUp(self):
        self.admin_client = Client()
        self.admin_client.force_login(
            User.objects.create_user(username="ADMIN1", password=PASSWORD, role=Role.ADMIN)
        )
        self.student = make_student("21CS001")
        self.bystander = make_student("21CS002")
        self.bystander_client = Client()
        self.bystander_client.force_login(self.bystander.user)

    def devices(self, user, count=2):
        clients = [Client() for _ in range(count)]
        for client in clients:
            client.force_login(user)
        self.assertEqual(sessions_of(user), count)
        return clients

    def assert_signed_out(self, clients):
        for client in clients:
            response = client.get(reverse("dashboard"))
            self.assertRedirects(response, f"{reverse('login')}?next={reverse('dashboard')}")

    def assert_bystander_untouched(self):
        self.assertEqual(sessions_of(self.bystander.user), 1)
        self.assertEqual(self.bystander_client.get(reverse("dashboard")).status_code, 302)
        self.assertIn(SESSION_KEY, self.bystander_client.session)

    def test_deactivating_a_student_deletes_every_session_row(self):
        phones = self.devices(self.student.user)
        self.admin_client.post(reverse("student_deactivate", args=[self.student.pk]))
        self.assertEqual(sessions_of(self.student.user), 0)
        self.assert_signed_out(phones)
        self.assert_bystander_untouched()

    def test_deleting_a_student_deletes_every_session_row(self):
        self.devices(self.student.user)
        user_pk = self.student.user.pk
        self.admin_client.post(
            reverse("student_delete", args=[self.student.pk]), {"reason": "Created in error"}
        )
        self.assertFalse(User.objects.filter(pk=user_pk).exists())
        self.assertFalse(any(s.get_decoded().get(SESSION_KEY) == str(user_pk) for s in Session.objects.all()))
        self.assert_bystander_untouched()

    def test_deactivating_and_deleting_faculty_delete_their_session_rows(self):
        member = make_faculty("F001")
        laptops = self.devices(member.user)
        self.admin_client.post(reverse("faculty_deactivate", args=[member.pk]))
        self.assertEqual(sessions_of(member.user), 0)
        self.assert_signed_out(laptops)

        member.user.is_active = True
        member.user.save()
        self.devices(member.user, count=1)
        user_pk = member.user.pk
        self.admin_client.post(reverse("faculty_delete", args=[member.pk]), {"reason": "Left the college"})
        self.assertFalse(any(s.get_decoded().get(SESSION_KEY) == str(user_pk) for s in Session.objects.all()))

    def test_deactivation_outside_the_admin_pages_also_ends_sessions(self):
        # For example through the Django admin site, which saves the whole user record.
        self.devices(self.student.user)
        self.student.user.is_active = False
        self.student.user.save()
        self.assertEqual(sessions_of(self.student.user), 0)

    def test_ordinary_saves_and_new_logins_keep_existing_sessions(self):
        first, _second = self.devices(self.student.user)
        self.student.user.email = "first@example.edu"
        self.student.user.save()
        self.student.user.save(update_fields=["last_login"])
        self.assertEqual(sessions_of(self.student.user), 2)
        self.assertEqual(first.get(reverse("dashboard")).status_code, 302)
        self.assertIn(SESSION_KEY, first.session)

    def test_helper_reports_how_many_sessions_it_ended(self):
        self.devices(self.student.user, count=3)
        self.assertEqual(end_user_sessions(self.student.user.pk), 3)
        self.assertEqual(end_user_sessions(self.student.user.pk), 0)
        self.assert_bystander_untouched()


class ExpiredSessionCleanupTests(TestCase):
    def test_clearsessions_removes_only_expired_rows(self):
        # The daily scheduled `clearsessions` job (README) removes sessions that timed out.
        expired = SessionStore()
        expired["note"] = "idle timeout passed"
        expired.create()
        Session.objects.filter(pk=expired.session_key).update(
            expire_date=timezone.now() - timedelta(minutes=1)
        )
        current = SessionStore()
        current["note"] = "still in use"
        current.create()

        call_command("clearsessions")

        self.assertFalse(Session.objects.filter(pk=expired.session_key).exists())
        self.assertTrue(Session.objects.filter(pk=current.session_key).exists())
