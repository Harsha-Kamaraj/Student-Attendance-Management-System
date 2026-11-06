"""Part 3: close the invalid-email and blank-section gaps in the test plan."""

from django.core import mail
from django.test import TestCase
from django.urls import reverse

from apps.academics.models import Section, Student
from apps.accounts.models import Role, User


class TestPlanValidationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = User.objects.create_user(username="PART3ADMIN", role=Role.ADMIN)
        cls.section = Section.objects.create(class_name="CSE Semester 5", name="A", year=2026)

    def setUp(self):
        self.client.force_login(self.admin)

    def test_invalid_student_email_does_not_create_account_or_send_credentials(self):
        """UT_02_3: a malformed address must leave both account and profile unsaved."""
        response = self.client.post(
            reverse("student_create"),
            {
                "roll_number": "PART3S001",
                "full_name": "Synthetic Student",
                "class_name": self.section.class_name,
                "home_section": self.section.pk,
                "email": "abc",
            },
        )
        self.assertContains(response, "Enter a valid email address.")
        self.assertFormError(response.context["form"], "email", "Enter a valid email address.")
        self.assertFalse(User.objects.filter(username="PART3S001").exists())
        self.assertFalse(Student.objects.filter(roll_number="PART3S001").exists())
        self.assertEqual(len(mail.outbox), 0)

    def test_blank_required_section_fields_do_not_create_section(self):
        """UT_05_2: department/semester and section are required; batch year is optional."""
        for data, missing in [
            ({"class_name": "", "name": ""}, ("class_name", "name")),
            ({"class_name": "", "name": "B"}, ("class_name",)),
            ({"class_name": "CSE Semester 5", "name": ""}, ("name",)),
        ]:
            with self.subTest(data=data):
                response = self.client.post(reverse("section_create"), data)
                self.assertEqual(response.status_code, 200)
                for field in missing:
                    self.assertFormError(response.context["form"], field, "This field is required.")
                self.assertEqual(Section.objects.count(), 1)
