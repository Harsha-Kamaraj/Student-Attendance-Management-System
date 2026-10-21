"""BL-11: assign faculty and subjects to classes."""

from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import Role, User
from apps.accounts.permissions import can_mark_attendance, visible_students
from apps.audit.models import AuditEntry

from .models import Enrollment, Section, Subject, TeachingAssignment
from .tests import make_faculty, make_student

PASSWORD = "Attend#2026"


class TeachingAssignmentTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(username="ADMIN1", password=PASSWORD, role=Role.ADMIN)
        self.f1, self.f2 = make_faculty("F001"), make_faculty("F002")
        self.section = Section.objects.create(class_name="B.Tech CSE Year 2", name="A")
        self.other = Section.objects.create(class_name="B.Tech CSE Year 2", name="B")
        self.cs101 = Subject.objects.create(code="CS101", name="Programming")
        self.cs102 = Subject.objects.create(code="CS102", name="Data Structures")
        self.client.login(username="ADMIN1", password=PASSWORD)

    def assign(self, subject, faculty, section=None):
        section = section or self.section
        return self.client.post(
            reverse("class_assign", args=[section.pk]), {"subject": subject.pk, "faculty": faculty.pk}
        )

    def set_teacher(self, assignment, faculty):
        return self.client.post(
            reverse("class_teacher", args=[assignment.section_id, assignment.pk]),
            {"faculty": faculty.pk if faculty else ""},
        )

    # AC 1 --------------------------------------------------------------------------------
    def test_admin_links_faculty_and_subject_to_section(self):
        response = self.assign(self.cs101, self.f1)
        self.assertRedirects(response, reverse("section_detail", args=[self.section.pk]))
        assignment = TeachingAssignment.objects.get(section=self.section, subject=self.cs101)
        self.assertEqual(assignment.faculty, self.f1)
        entry = AuditEntry.objects.get(action="assignment.create")
        self.assertEqual(
            entry.new_value, {"section": "B.Tech CSE Year 2 A", "subject": "CS101", "faculty": "F001"}
        )

    def test_section_page_shows_subject_and_teacher(self):
        self.assign(self.cs101, self.f1)
        page = self.client.get(reverse("section_detail", args=[self.section.pk]))
        self.assertContains(page, "CS101")
        self.assertContains(page, "Faculty F001")
        self.assertContains(page, "Change teacher")

    def test_admin_assigns_teacher_to_subject_offered_without_one(self):
        offered = TeachingAssignment.objects.create(section=self.section, subject=self.cs102)
        self.set_teacher(offered, self.f2)
        offered.refresh_from_db()
        self.assertEqual(offered.faculty, self.f2)

    # AC 2 --------------------------------------------------------------------------------
    def test_missing_subject_or_teacher_is_rejected(self):
        # What a browser sends when both drop-downs are left on their placeholder.
        response = self.client.post(
            reverse("class_assign", args=[self.section.pk]), {"subject": "", "faculty": ""}
        )
        self.assertContains(response, "This field is required.", count=2)
        self.assertFalse(TeachingAssignment.objects.exists())

    def test_nonexistent_subject_and_faculty_are_rejected(self):
        response = self.client.post(
            reverse("class_assign", args=[self.section.pk]), {"subject": 99999, "faculty": 99999}
        )
        self.assertContains(response, "Select a valid choice", count=2)
        self.assertFalse(TeachingAssignment.objects.exists())

    def test_nonexistent_section_is_not_found(self):
        response = self.client.post(
            reverse("class_assign", args=[99999]), {"subject": self.cs101.pk, "faculty": self.f1.pk}
        )
        self.assertEqual(response.status_code, 404)

    def test_subject_already_in_section_is_rejected(self):
        self.assign(self.cs101, self.f1)
        response = self.assign(self.cs101, self.f2)
        self.assertContains(response, "Select a valid choice")
        self.assertEqual(TeachingAssignment.objects.get(subject=self.cs101).faculty, self.f1)

    def test_deactivated_faculty_cannot_be_chosen(self):
        self.f2.user.is_active = False
        self.f2.user.save()
        response = self.assign(self.cs101, self.f2)
        self.assertContains(response, "Select a valid choice")
        offered = TeachingAssignment.objects.create(section=self.section, subject=self.cs102)
        self.set_teacher(offered, self.f2)
        offered.refresh_from_db()
        self.assertIsNone(offered.faculty)

    def test_class_from_another_section_url_is_not_found(self):
        assignment = TeachingAssignment.objects.create(
            section=self.other, subject=self.cs101, faculty=self.f1
        )
        response = self.client.post(
            reverse("class_teacher", args=[self.section.pk, assignment.pk]), {"faculty": self.f2.pk}
        )
        self.assertEqual(response.status_code, 404)
        assignment.refresh_from_db()
        self.assertEqual(assignment.faculty, self.f1)

    # AC 3 --------------------------------------------------------------------------------
    def test_assignment_persists_after_logout_and_login(self):
        self.assign(self.cs101, self.f1)
        self.client.logout()
        self.client.login(username="ADMIN1", password=PASSWORD)
        self.assertContains(
            self.client.get(reverse("section_detail", args=[self.section.pk])), "Faculty F001"
        )

    # AC 4 --------------------------------------------------------------------------------
    def test_faculty_see_only_their_classes_with_student_counts(self):
        self.assign(self.cs101, self.f1)
        self.assign(self.cs102, self.f2, section=self.other)
        Enrollment.objects.create(
            student=make_student("21CS001"), assignment=TeachingAssignment.objects.get(subject=self.cs101)
        )
        self.client.logout()
        self.client.login(username="F001", password=PASSWORD)
        page = self.client.get(reverse("my_classes"))
        self.assertContains(page, "CS101")
        self.assertNotContains(page, "CS102")
        self.assertEqual([c.student_count for c in page.context["classes"]], [1])

    def test_faculty_without_classes_sees_empty_message(self):
        self.client.logout()
        self.client.login(username="F002", password=PASSWORD)
        self.assertContains(self.client.get(reverse("my_classes")), "No classes are assigned to you yet.")

    def test_my_classes_is_for_faculty_only(self):
        make_student("21CS001")
        for username in ("ADMIN1", "21CS001"):
            with self.subTest(user=username):
                self.client.logout()
                self.client.login(username=username, password=PASSWORD)
                self.assertEqual(self.client.get(reverse("my_classes")).status_code, 403)

    # AC 5 --------------------------------------------------------------------------------
    def test_changing_teacher_moves_attendance_access(self):
        self.assign(self.cs101, self.f1)
        assignment = TeachingAssignment.objects.get(subject=self.cs101)
        student = make_student("21CS001")
        Enrollment.objects.create(student=student, assignment=assignment)
        self.assertTrue(can_mark_attendance(self.f1.user, assignment))
        self.assertIn(student, visible_students(self.f1.user))

        self.set_teacher(assignment, self.f2)
        assignment.refresh_from_db()
        self.assertFalse(can_mark_attendance(self.f1.user, assignment))
        self.assertTrue(can_mark_attendance(self.f2.user, assignment))
        self.assertNotIn(student, visible_students(self.f1.user))
        entry = AuditEntry.objects.get(action="assignment.teacher")
        self.assertEqual((entry.old_value, entry.new_value), ({"faculty": "F001"}, {"faculty": "F002"}))

    def test_removing_teacher_blocks_faculty_marking_and_frees_them_for_deactivation(self):
        # BL-11 decision + BL-08: removing the teacher lets the Admin deactivate them.
        self.assign(self.cs101, self.f1)
        assignment = TeachingAssignment.objects.get(subject=self.cs101)
        self.set_teacher(assignment, None)
        assignment.refresh_from_db()
        self.assertIsNone(assignment.faculty)
        self.assertFalse(can_mark_attendance(self.f1.user, assignment))
        self.assertTrue(can_mark_attendance(self.admin, assignment))
        self.client.post(reverse("faculty_deactivate", args=[self.f1.pk]))
        self.f1.user.refresh_from_db()
        self.assertFalse(self.f1.user.is_active)

    def test_saving_same_teacher_changes_nothing(self):
        self.assign(self.cs101, self.f1)
        assignment = TeachingAssignment.objects.get(subject=self.cs101)
        self.set_teacher(assignment, self.f1)
        self.assertFalse(AuditEntry.objects.filter(action="assignment.teacher").exists())

    # Permissions -----------------------------------------------------------------------
    def test_non_admins_cannot_assign_or_change_teachers(self):
        assignment = TeachingAssignment.objects.create(
            section=self.section, subject=self.cs101, faculty=self.f1
        )
        make_student("21CS001")
        for username in ("F002", "21CS001"):
            with self.subTest(user=username):
                self.client.logout()
                self.client.login(username=username, password=PASSWORD)
                add = self.assign(self.cs102, self.f2)
                change = self.set_teacher(assignment, self.f2)
                self.assertEqual((add.status_code, change.status_code), (403, 403))
        assignment.refresh_from_db()
        self.assertEqual(assignment.faculty, self.f1)
        self.assertFalse(TeachingAssignment.objects.filter(subject=self.cs102).exists())
