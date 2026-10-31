"""My profile: every signed-in user sees only their own details, read-only."""

from django.test import TestCase
from django.urls import reverse

from apps.academics.models import Enrollment, Section, Subject, TeachingAssignment
from apps.academics.tests import make_faculty, make_student

from .models import Role, User


class MyProfileTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.faculty = make_faculty("F001")
        cls.other_faculty = make_faculty("F002")
        cls.student = make_student("S001")
        section = Section.objects.create(class_name="B.Tech in CS 5th sem", name="K", year=2028)
        subject = Subject.objects.create(code="CS101", name="Programming")
        assignment = TeachingAssignment.objects.create(section=section, subject=subject, faculty=cls.faculty)
        TeachingAssignment.objects.create(
            section=section,
            subject=Subject.objects.create(code="MA101", name="Mathematics"),
            faculty=cls.other_faculty,
        )
        Enrollment.objects.create(student=cls.student, assignment=assignment)
        cls.admin = User.objects.create_user(username="ADMIN1", role=Role.ADMIN, email="admin@example.edu")

    def profile(self, user):
        self.client.force_login(user)
        return self.client.get(reverse("my_profile"))

    def test_admin_sees_account_details_and_change_password(self):
        response = self.profile(self.admin)
        self.assertContains(response, "My profile")
        self.assertContains(response, "admin@example.edu")
        self.assertContains(response, "Admin access")
        self.assertContains(response, reverse("password_change"))

    def test_faculty_see_their_details_and_only_their_classes(self):
        response = self.profile(self.faculty.user)
        self.assertContains(response, self.faculty.full_name)
        self.assertContains(response, "Faculty details")
        self.assertContains(response, "CS101 – Programming")
        self.assertContains(response, "B.Tech in CS 5th sem K (2028)")
        self.assertNotContains(response, "MA101")

    def test_student_sees_roll_number_subjects_and_teacher(self):
        response = self.profile(self.student.user)
        self.assertContains(response, "S001")
        self.assertContains(response, "CS101 – Programming")
        self.assertContains(response, self.faculty.full_name)

    def test_navbar_name_links_to_profile(self):
        self.client.force_login(self.admin)
        self.assertContains(self.client.get(reverse("dashboard_admin")), f'href="{reverse("my_profile")}"')

    def test_anonymous_users_must_log_in(self):
        response = self.client.get(reverse("my_profile"))
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response["Location"].startswith(reverse("login")))
