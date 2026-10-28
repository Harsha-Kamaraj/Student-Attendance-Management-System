"""BL-05: permission matrix, scope rules and denial handling."""

import datetime
from uuid import UUID

from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.test import TestCase
from django.urls import URLPattern, URLResolver, get_resolver, reverse
from django.urls.converters import UUIDConverter

from apps.academics.models import Enrollment, Section, Student, Subject, TeachingAssignment
from apps.academics.tests import make_faculty, make_student
from apps.attendance.models import AttendanceRecord, AttendanceSession, Status
from apps.audit import services as audit
from apps.audit.models import AuditEntry

from .models import Role, User
from .permissions import (
    PERMISSIONS,
    can_correct_attendance,
    can_delete_subject,
    can_edit_subject,
    can_mark_attendance,
    get_visible_or_deny,
    has_permission,
    visible_assignments,
    visible_attendance_history,
    visible_attendance_records,
    visible_students,
)

PASSWORD = "Attend#2026"
A, F, S = Role.ADMIN, Role.FACULTY, Role.STUDENT

# The agreed matrix (Documents/BL-05_Permission_Matrix.md), written out independently of the
# code so that an accidental change to PERMISSIONS fails this test.
EXPECTED_MATRIX = {
    "accounts.manage": {A},
    "students.manage": {A},
    "students.view": {A, F, S},
    "faculty.manage": {A},
    "subjects.create": {A, F},
    "subjects.edit": {A, F},
    "subjects.delete": {A},
    "sections.manage": {A},
    "attendance.mark": {A, F},
    "attendance.correct": {A, F},
    "attendance.view": {A, F, S},
    "attendance.history": {A, F},
    "reports.generate": {A, F},
    "reports.export": {A, F},
    "records.search": {A, F},
    "threshold.configure": {A},
    "low_attendance.view": {A, F},
    "notifications.view": {S},
    "backup.manage": {A},
    "audit.view": {A},
}


class MatrixTests(TestCase):
    def setUp(self):
        self.users = {
            role: User.objects.create_user(username=f"u_{role}", password=PASSWORD, role=role)
            for role in (A, F, S)
        }

    def test_code_matches_agreed_matrix(self):
        self.assertEqual(PERMISSIONS, EXPECTED_MATRIX)

    def test_every_role_and_action(self):
        for action, allowed in EXPECTED_MATRIX.items():
            for role, user in self.users.items():
                with self.subTest(action=action, role=role):
                    self.assertEqual(has_permission(user, action), role in allowed)

    def test_deactivated_user_has_no_permissions(self):
        admin = self.users[A]
        admin.is_active = False
        self.assertFalse(has_permission(admin, "accounts.manage"))

    def test_unknown_action_is_an_error(self):
        with self.assertRaises(KeyError):
            has_permission(self.users[A], "attendance.delete_everything")


class ScopeTests(TestCase):
    """Two classes: F1 teaches CS101 in section A (student S1); F2 teaches CS102 in section B (S2)."""

    def setUp(self):
        self.admin = User.objects.create_user(username="ADMIN1", password=PASSWORD, role=A)
        self.f1, self.f2 = make_faculty("F001"), make_faculty("F002")
        self.f3 = make_faculty("F003")  # no classes
        self.s1, self.s2 = make_student("21CS001"), make_student("21CS002")
        sec_a = Section.objects.create(class_name="B.Tech CSE Year 2", name="A")
        sec_b = Section.objects.create(class_name="B.Tech CSE Year 2", name="B")
        self.cs101 = Subject.objects.create(code="CS101", name="Programming")
        self.cs102 = Subject.objects.create(code="CS102", name="Data Structures")
        self.class_a = TeachingAssignment.objects.create(section=sec_a, subject=self.cs101, faculty=self.f1)
        self.class_b = TeachingAssignment.objects.create(section=sec_b, subject=self.cs102, faculty=self.f2)
        Enrollment.objects.create(student=self.s1, assignment=self.class_a)
        Enrollment.objects.create(student=self.s2, assignment=self.class_b)
        day = datetime.date(2026, 10, 6)
        sess_a = AttendanceSession.objects.create(assignment=self.class_a, date=day, period=1)
        sess_b = AttendanceSession.objects.create(assignment=self.class_b, date=day, period=1)
        self.rec_s1 = AttendanceRecord.objects.create(session=sess_a, student=self.s1, status=Status.PRESENT)
        self.rec_s2 = AttendanceRecord.objects.create(session=sess_b, student=self.s2, status=Status.ABSENT)
        for rec in (self.rec_s1, self.rec_s2):
            audit.record(
                "attendance.correct",
                actor=self.admin,
                target_type="AttendanceRecord",
                target_id=rec.pk,
                old_value={"status": "A"},
                new_value={"status": rec.status},
            )
        audit.record("account.create", actor=self.admin, target_type="User", target_id=self.s1.user.pk)

    def test_admin_sees_everything(self):
        self.assertEqual(visible_students(self.admin).count(), 2)
        self.assertEqual(visible_attendance_records(self.admin).count(), 2)
        self.assertEqual(visible_assignments(self.admin).count(), 2)

    def test_faculty_sees_only_their_classes(self):
        # SEC-13
        self.assertEqual(list(visible_students(self.f1.user)), [self.s1])
        self.assertEqual(list(visible_attendance_records(self.f1.user)), [self.rec_s1])
        self.assertEqual(list(visible_assignments(self.f1.user)), [self.class_a])

    def test_faculty_without_classes_sees_nothing(self):
        self.assertFalse(visible_students(self.f3.user).exists())
        self.assertFalse(visible_attendance_records(self.f3.user).exists())

    def test_student_sees_only_themselves(self):
        # SEC-12
        self.assertEqual(list(visible_students(self.s1.user)), [self.s1])
        self.assertEqual(list(visible_attendance_records(self.s1.user)), [self.rec_s1])
        self.assertEqual(list(visible_assignments(self.s1.user)), [self.class_a])

    def test_student_cannot_fetch_another_students_record_by_id(self):
        # AC 3, SEC-12, IT_08_2
        own = get_visible_or_deny(visible_attendance_records(self.s1.user), AttendanceRecord, self.rec_s1.pk)
        self.assertEqual(own, self.rec_s1)
        with self.assertRaises(PermissionDenied):
            get_visible_or_deny(visible_attendance_records(self.s1.user), AttendanceRecord, self.rec_s2.pk)
        with self.assertRaises(PermissionDenied):
            get_visible_or_deny(visible_students(self.s1.user), Student, self.s2.pk)

    def test_missing_record_is_not_found(self):
        with self.assertRaises(Http404):
            get_visible_or_deny(visible_attendance_records(self.admin), AttendanceRecord, 999999)

    def test_faculty_can_mark_only_their_own_classes(self):
        # AC 4, SEC-13, ST_06_2
        self.assertTrue(can_mark_attendance(self.f1.user, self.class_a))
        self.assertFalse(can_mark_attendance(self.f1.user, self.class_b))
        self.assertFalse(can_mark_attendance(self.f3.user, self.class_a))
        self.assertFalse(can_mark_attendance(self.s1.user, self.class_a))
        self.assertTrue(can_mark_attendance(self.admin, self.class_b))  # missed session with reason (AR-08)

    def test_faculty_can_correct_only_their_own_classes(self):
        # AC 4, SEC-13, IT_07_2
        self.assertTrue(can_correct_attendance(self.f1.user, self.rec_s1))
        self.assertFalse(can_correct_attendance(self.f1.user, self.rec_s2))
        self.assertFalse(can_correct_attendance(self.s1.user, self.rec_s1))
        self.assertTrue(can_correct_attendance(self.admin, self.rec_s2))

    def test_subject_rules(self):
        # FR-05 and BL-05 decision: faculty edit subjects they teach; only Admin deletes
        self.assertTrue(can_edit_subject(self.f1.user, self.cs101))
        self.assertFalse(can_edit_subject(self.f1.user, self.cs102))
        self.assertTrue(can_edit_subject(self.admin, self.cs102))
        self.assertFalse(can_edit_subject(self.s1.user, self.cs101))
        self.assertTrue(can_delete_subject(self.admin, self.cs101))
        self.assertFalse(can_delete_subject(self.f1.user, self.cs101))

    def test_attendance_history_visibility(self):
        # BL-05 decision: Admin all; Faculty own classes; Students none
        self.assertEqual(visible_attendance_history(self.admin).count(), 3)
        faculty_view = visible_attendance_history(self.f1.user)
        self.assertEqual(list(faculty_view.values_list("target_id", flat=True)), [str(self.rec_s1.pk)])
        self.assertFalse(visible_attendance_history(self.s1.user).exists())
        self.assertFalse(visible_attendance_history(self.f3.user).exists())

    def test_moving_a_class_moves_the_access(self):
        self.class_a.faculty = self.f3
        self.class_a.save()
        self.assertFalse(can_mark_attendance(self.f1.user, self.class_a))
        self.assertTrue(can_mark_attendance(self.f3.user, self.class_a))


class LoginRequiredEverywhereTests(TestCase):
    """SEC-01: every page except the public ones redirects anonymous users to login."""

    PUBLIC = {"home", "login"}

    def named_routes(self, resolver=None):
        for pattern in (resolver or get_resolver()).url_patterns:
            if isinstance(pattern, URLResolver):
                if pattern.app_name != "admin":
                    yield from self.named_routes(pattern)
            elif isinstance(pattern, URLPattern) and pattern.name:
                yield pattern

    def test_every_app_page_requires_login(self):
        checked = 0
        for pattern in self.named_routes():
            if pattern.name in self.PUBLIC:
                continue
            kwargs = {
                name: UUID(int=1) if isinstance(converter, UUIDConverter) else 1
                for name, converter in pattern.pattern.converters.items()
            }
            url = reverse(pattern.name, kwargs=kwargs)
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 302)
                self.assertTrue(response["Location"].startswith(reverse("login")))
                checked += 1
        self.assertGreaterEqual(checked, 8)

    def test_public_pages_are_open(self):
        for name in self.PUBLIC:
            with self.subTest(page=name):
                self.assertEqual(self.client.get(reverse(name)).status_code, 200)

    def test_django_admin_login_is_open(self):
        self.assertEqual(self.client.get("/admin/login/").status_code, 200)


class DenialTests(TestCase):
    """AC 5: refused requests show no protected data, change nothing, and are logged."""

    def setUp(self):
        self.admin = User.objects.create_user(username="ADMIN1", password=PASSWORD, role=A)
        self.student = User.objects.create_user(username="21CS001", password=PASSWORD, role=S)
        self.faculty = User.objects.create_user(username="F001", password=PASSWORD, role=F)

    def test_student_opening_account_list_sees_no_account_data(self):
        self.client.login(username="21CS001", password=PASSWORD)
        response = self.client.get(reverse("account_list"))
        self.assertEqual(response.status_code, 403)
        self.assertContains(response, "Access denied", status_code=403)
        self.assertNotContains(response, "ADMIN1", status_code=403)
        self.assertNotContains(response, "F001", status_code=403)

    def test_denied_request_changes_nothing(self):
        self.client.login(username="F001", password=PASSWORD)
        before = self.admin.password
        create = self.client.post(
            reverse("account_create"), {"username": "HACK1", "role": "ADMIN", "email": "h@x.edu"}
        )
        reset = self.client.post(reverse("account_reset_password", args=[self.admin.pk]))
        self.assertEqual((create.status_code, reset.status_code), (403, 403))
        self.assertFalse(User.objects.filter(username="HACK1").exists())
        self.admin.refresh_from_db()
        self.assertEqual(self.admin.password, before)

    def test_denial_is_logged_with_user_and_path(self):
        # SEC-12, SEC-22
        self.client.login(username="21CS001", password=PASSWORD)
        self.client.get(reverse("account_list"))
        entry = AuditEntry.objects.get(action="access.denied")
        self.assertEqual(entry.actor_username, "21CS001")
        self.assertEqual(entry.target_id, "GET /users/")

    def test_role_dashboards_deny_other_roles(self):
        self.client.login(username="F001", password=PASSWORD)
        for name in ("dashboard_admin", "dashboard_student"):
            with self.subTest(page=name):
                self.assertEqual(self.client.get(reverse(name)).status_code, 403)
        self.assertEqual(AuditEntry.objects.filter(action="access.denied").count(), 2)
