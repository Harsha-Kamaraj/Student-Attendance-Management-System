"""BL-08 / UC-03: faculty management."""

import datetime
import html

from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import Role, User
from apps.attendance.models import AttendanceSession
from apps.audit.models import AuditEntry

from .models import Faculty, Section, Subject, TeachingAssignment
from .tests import make_faculty

PASSWORD = "Attend#2026"


class FacultyTestBase(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(username="ADMIN1", password=PASSWORD, role=Role.ADMIN)
        self.teacher = make_faculty("F001")  # teaches CS101 in section A
        self.free = make_faculty("F002")  # no classes
        self.section = Section.objects.create(class_name="B.Tech CSE Year 2", name="A")
        self.subject = Subject.objects.create(code="CS101", name="Programming")
        self.assignment = TeachingAssignment.objects.create(
            section=self.section, subject=self.subject, faculty=self.teacher
        )
        self.client.login(username="ADMIN1", password=PASSWORD)

    def create(self, **data):
        values = {
            "faculty_id": "f010",
            "full_name": "Dr. Meera Iyer",
            "department": "CSE",
            "email": "m@x.edu",
        }
        return self.client.post(reverse("faculty_create"), values | data)


class CreateAndViewTests(FacultyTestBase):
    def test_admin_adds_faculty_with_login_and_temporary_password(self):
        # UT_03_1, AC 1, BL-01 D-02
        response = self.create()
        member = Faculty.objects.get(faculty_id="F010")
        self.assertEqual((member.full_name, member.department), ("Dr. Meera Iyer", "CSE"))
        self.assertEqual(member.user.username, "F010")
        self.assertEqual(member.user.role, Role.FACULTY)
        self.assertTrue(member.user.must_change_password)
        raw = response.content.decode().split('data-testid="temporary-password">')[1].split("<")[0]
        self.assertTrue(member.user.check_password(html.unescape(raw)))
        self.assertIn("no-store", response["Cache-Control"])
        self.assertTrue(AuditEntry.objects.filter(action="faculty.create").exists())

    def test_new_faculty_can_log_in_and_is_forced_to_change_password(self):
        response = self.create()
        raw = response.content.decode().split('data-testid="temporary-password">')[1].split("<")[0]
        self.client.logout()
        login = self.client.post(reverse("login"), {"username": "f010", "password": html.unescape(raw)})
        self.assertRedirects(login, reverse("dashboard"), fetch_redirect_response=False)
        self.assertRedirects(self.client.get(reverse("dashboard")), reverse("password_change"))

    def test_list_and_detail_show_faculty_and_their_classes(self):
        self.assertContains(self.client.get(reverse("faculty_list")), "F001")
        detail = self.client.get(reverse("faculty_detail", args=[self.teacher.pk]))
        self.assertContains(detail, "CS101")
        self.assertContains(detail, "B.Tech CSE Year 2 A")

    def test_required_fields_are_validated(self):
        # UT_03_2, AC 2
        response = self.create(faculty_id="", full_name="  ", department="", email="bad")
        self.assertContains(response, "This field is required.")
        self.assertContains(response, "Enter a valid email address.")
        self.assertEqual(Faculty.objects.count(), 2)

    def test_duplicate_faculty_id_is_rejected_ignoring_case(self):
        # UT_03_3, ST_03_2, UC-03 3a
        response = self.create(faculty_id="f001")
        self.assertContains(response, "This faculty ID already exists.")
        self.assertEqual(Faculty.objects.filter(faculty_id__iexact="F001").count(), 1)

    def test_faculty_id_cannot_reuse_an_existing_username(self):
        User.objects.create_user(username="21CS001", password=PASSWORD, role=Role.STUDENT)
        self.assertContains(self.create(faculty_id="21cs001"), "This faculty ID already exists.")


class EditTests(FacultyTestBase):
    def test_admin_updates_details_and_change_persists(self):
        # AC 3, IT_03_3
        self.client.post(
            reverse("faculty_edit", args=[self.free.pk]),
            {"full_name": "Dr. Kumar", "department": "ECE", "email": "k@x.edu"},
        )
        self.client.logout()
        self.client.login(username="ADMIN1", password=PASSWORD)
        detail = self.client.get(reverse("faculty_detail", args=[self.free.pk]))
        self.assertContains(detail, "Dr. Kumar")
        self.assertContains(detail, "ECE")
        self.assertContains(detail, "k@x.edu")
        entry = AuditEntry.objects.get(action="faculty.update")
        self.assertEqual((entry.old_value, entry.new_value), ({"department": "CSE"}, {"department": "ECE"}))

    def test_faculty_id_is_not_editable(self):
        self.client.post(
            reverse("faculty_edit", args=[self.free.pk]),
            {"faculty_id": "ZZ9", "full_name": "X", "department": "CSE", "email": "x@x.edu"},
        )
        self.free.refresh_from_db()
        self.assertEqual((self.free.faculty_id, self.free.user.username), ("F002", "F002"))


class DeactivateAndDeleteTests(FacultyTestBase):
    def test_faculty_with_classes_cannot_be_deactivated(self):
        # AC 4, ST_03_3, UC-03 4a, BL-01 D-03
        response = self.client.post(reverse("faculty_deactivate", args=[self.teacher.pk]), follow=True)
        self.assertContains(response, "reassign their classes first (CS101 in B.Tech CSE Year 2 A)")
        self.teacher.user.refresh_from_db()
        self.assertTrue(self.teacher.user.is_active)

    def test_faculty_with_classes_cannot_be_deleted(self):
        # AC 4, ST_03_3, BL-01 D-04
        response = self.client.post(
            reverse("faculty_delete", args=[self.teacher.pk]), {"reason": "Left"}, follow=True
        )
        self.assertContains(response, "reassign their classes first")
        self.assertTrue(Faculty.objects.filter(pk=self.teacher.pk).exists())

    def test_reassigning_classes_then_deactivating_works(self):
        self.assignment.faculty = self.free
        self.assignment.save()
        self.client.post(reverse("faculty_deactivate", args=[self.teacher.pk]))
        self.teacher.user.refresh_from_db()
        self.assertFalse(self.teacher.user.is_active)

    def test_deactivated_faculty_cannot_log_in_and_reactivation_restores_access(self):
        # AC 5, SEC-15, ST_03_5
        self.client.post(reverse("faculty_deactivate", args=[self.free.pk]))
        other = self.client_class()
        response = other.post(reverse("login"), {"username": "F002", "password": PASSWORD})
        self.assertContains(response, "This account is deactivated. Contact the Admin.")

        self.client.post(reverse("faculty_reactivate", args=[self.free.pk]))
        self.assertTrue(other.login(username="F002", password=PASSWORD))
        actions = set(AuditEntry.objects.values_list("action", flat=True))
        self.assertTrue({"faculty.deactivate", "faculty.reactivate"} <= actions)

    def test_deactivation_ends_an_open_session(self):
        session = self.client_class()
        session.login(username="F002", password=PASSWORD)
        self.client.post(reverse("faculty_deactivate", args=[self.free.pk]))
        response = session.get(reverse("dashboard_faculty"))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("login"), response["Location"])

    def test_delete_requires_a_reason(self):
        self.client.post(reverse("faculty_delete", args=[self.free.pk]), {"reason": "  "})
        self.assertTrue(Faculty.objects.filter(pk=self.free.pk).exists())

    def test_delete_keeps_attendance_they_recorded(self):
        # AC 5, ST_03_4, BL-01 D-04
        session = AttendanceSession.objects.create(
            assignment=self.assignment,
            date=datetime.date(2026, 10, 6),
            period=1,
            recorded_by=self.free.user,
            recorded_by_code="F002",
        )
        confirm = self.client.get(reverse("faculty_delete", args=[self.free.pk]))
        self.assertContains(confirm, "The 1 attendance session(s)")
        self.client.post(reverse("faculty_delete", args=[self.free.pk]), {"reason": "Left the institution"})
        self.assertFalse(User.objects.filter(username="F002").exists())
        session.refresh_from_db()
        self.assertIsNone(session.recorded_by)
        self.assertEqual(session.recorded_by_code, "F002")
        entry = AuditEntry.objects.get(action="faculty.delete")
        self.assertEqual(entry.reason, "Left the institution")

    def test_deactivate_requires_post(self):
        self.assertEqual(self.client.get(reverse("faculty_deactivate", args=[self.free.pk])).status_code, 405)


class PermissionTests(FacultyTestBase):
    def test_non_admins_cannot_manage_faculty(self):
        # AC 6, IT_03_2, SEC-14
        make_student_user = User.objects.create_user(username="21CS001", password=PASSWORD, role=Role.STUDENT)
        for username in ("F001", make_student_user.username):
            with self.subTest(user=username):
                self.client.logout()
                self.client.login(username=username, password=PASSWORD)
                urls = [
                    ("get", reverse("faculty_list")),
                    ("post", reverse("faculty_create")),
                    ("post", reverse("faculty_edit", args=[self.free.pk])),
                    ("post", reverse("faculty_deactivate", args=[self.free.pk])),
                    ("post", reverse("faculty_delete", args=[self.free.pk])),
                ]
                for method, url in urls:
                    response = getattr(self.client, method)(url, {"reason": "x", "faculty_id": "HACK"})
                    self.assertEqual(response.status_code, 403, url)
        self.free.user.refresh_from_db()
        self.assertTrue(self.free.user.is_active)
        self.assertFalse(Faculty.objects.filter(faculty_id="HACK").exists())
