"""Saving a new student or faculty member returns to the list (13 Nov 2026 usability fix).

The confirmation page is kept only when the email failed and the one-time password must be shown.
A double click on Save must not send the form twice (handled in static/js/nav.js).
"""

from pathlib import Path
from unittest.mock import patch

from django.conf import settings
from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse

from apps.accounts.models import Role, User

from .models import Faculty, Section, Student

PASSWORD = "Attend#2026"


@override_settings(SITE_URL="https://attendance.example.edu")
class SaveReturnsToListTests(TestCase):
    def setUp(self):
        User.objects.create_user(username="ADMIN1", password=PASSWORD, role=Role.ADMIN)
        self.section = Section.objects.create(class_name="CSE 5", name="K")
        self.client.login(username="ADMIN1", password=PASSWORD)

    def add_faculty(self, **extra):
        data = {"faculty_id": "F001", "full_name": "Shravya", "department": "CSE", "email": "f@example.edu"}
        return self.client.post(reverse("faculty_create"), data, **extra)

    def add_student(self, **extra):
        data = {
            "roll_number": "S001",
            "full_name": "Asha",
            "class_name": "CSE 5",
            "home_section": self.section.pk,
            "email": "s@example.edu",
        }
        return self.client.post(reverse("student_create"), data, **extra)

    def test_faculty_save_goes_to_faculty_list_with_message(self):
        response = self.add_faculty(follow=True)
        self.assertRedirects(response, reverse("faculty_list"))
        self.assertContains(response, "Faculty F001 added. Login details sent to f***@example.edu")
        self.assertContains(response, "Shravya")
        self.assertEqual(len(mail.outbox), 1)

    def test_student_save_goes_to_student_list_with_message(self):
        response = self.add_student(follow=True)
        self.assertRedirects(response, reverse("student_list"))
        self.assertContains(response, "Student S001 added. Login details sent to s***@example.edu")
        self.assertEqual(len(mail.outbox), 1)

    def test_second_submit_of_same_id_creates_nothing_and_sends_no_second_email(self):
        self.add_faculty()
        again = self.add_faculty()
        self.assertContains(again, "This faculty ID already exists.")
        self.assertEqual(Faculty.objects.count(), 1)
        self.assertEqual(len(mail.outbox), 1)

    @override_settings(EMAIL_BACKEND="django.core.mail.backends.console.EmailBackend", DEBUG=True)
    def test_development_preview_also_returns_to_list(self):
        with patch("sys.stdout"):
            response = self.add_student(follow=True)
        self.assertRedirects(response, reverse("student_list"))
        self.assertContains(response, "were printed to the server console")
        self.assertTrue(Student.objects.filter(roll_number="S001").exists())

    def test_failed_email_stays_on_page_to_show_password_once(self):
        with patch("apps.accounts.credentials.EmailMessage.send", side_effect=RuntimeError("down")):
            response = self.add_faculty()
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "could not be emailed")
        self.assertContains(response, 'data-testid="temporary-password"')

    def test_pages_load_the_double_submit_guard(self):
        page = self.client.get(reverse("faculty_create"))
        self.assertContains(page, "js/nav.js?v=2026-11-13a")
        script = Path(settings.BASE_DIR, "static", "js", "nav.js").read_text()
        self.assertIn('form.dataset.submitting === "1"', script)
        self.assertIn("event.preventDefault()", script)

    def test_subject_save_goes_to_subject_list_with_message(self):
        response = self.client.post(
            reverse("subject_create"), {"code": "ue24cs352a", "name": "Machine Learning"}, follow=True
        )
        self.assertRedirects(response, reverse("subject_list"))
        self.assertContains(response, "Subject UE24CS352A created.")
        self.assertContains(response, "Machine Learning")

    def test_section_save_goes_to_section_list_with_message(self):
        response = self.client.post(
            reverse("section_create"), {"class_name": "CSE 5", "name": "L", "year": "2028"}, follow=True
        )
        self.assertRedirects(response, reverse("section_list"))
        self.assertContains(response, "Section CSE 5 L (2028) created.")

    def test_password_pages_load_the_show_password_button(self):
        self.client.logout()
        page = self.client.get(reverse("login"))
        self.assertContains(page, "js/password-toggle.js?v=2026-11-13a")
        script = Path(settings.BASE_DIR, "static", "js", "password-toggle.js").read_text()
        self.assertIn('input[type="password"]', script)
        self.assertIn('"Show password"', script)
        # The password is hidden again before the form is sent.
        self.assertIn('addEventListener("submit"', script)
