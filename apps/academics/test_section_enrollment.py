"""UC-05: section creation and enrollment constraints (BL-10)."""

from datetime import date

from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import Role, User
from apps.attendance.models import AttendanceRecord, AttendanceSession
from apps.audit.models import AuditEntry

from .models import Enrollment, Section, Student, Subject, TeachingAssignment
from .tests import make_faculty, make_student

PASSWORD = "Attend#2026"


class SectionEnrollmentTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(username="ADMIN1", password=PASSWORD, role=Role.ADMIN)
        self.faculty = User.objects.create_user(username="F001", password=PASSWORD, role=Role.FACULTY)
        self.student_user = User.objects.create_user(username="21CS001", password=PASSWORD, role=Role.STUDENT)
        self.student = Student.objects.create(
            user=self.student_user, roll_number="21CS001", full_name="Student 1"
        )
        self.section_a = Section.objects.create(class_name="B.Tech CSE Year 2", name="A")
        self.section_b = Section.objects.create(class_name="B.Tech CSE Year 2", name="B")
        self.subject = Subject.objects.create(code="CS101", name="Programming")
        self.assignment_a = TeachingAssignment.objects.create(section=self.section_a, subject=self.subject)
        self.assignment_b = TeachingAssignment.objects.create(section=self.section_b, subject=self.subject)

    def test_admin_can_create_and_view_sections(self):
        self.client.force_login(self.admin)
        response = self.client.post(
            reverse("section_create"), {"class_name": " B.Tech CSE Year 3 ", "name": " c "}
        )
        section = Section.objects.get(class_name="B.Tech CSE Year 3", name="C")
        self.assertRedirects(response, reverse("section_detail", args=[section.pk]))
        self.assertContains(self.client.get(reverse("section_list")), "B.Tech CSE Year 3")
        self.assertTrue(AuditEntry.objects.filter(action="section.create").exists())

    def test_duplicate_section_is_rejected(self):
        self.client.force_login(self.admin)
        response = self.client.post(
            reverse("section_create"), {"class_name": "b.tech cse year 2", "name": "a"}
        )
        self.assertContains(response, "That section already exists")
        self.assertEqual(Section.objects.count(), 2)

    def test_section_year_is_optional_and_part_of_the_name(self):
        self.client.force_login(self.admin)
        self.client.post(
            reverse("section_create"), {"class_name": "B.Tech in CS 5th sem", "name": "k", "year": "2028"}
        )
        section = Section.objects.get(class_name="B.Tech in CS 5th sem", name="K")
        self.assertEqual((section.year, str(section)), (2028, "B.Tech in CS 5th sem K (2028)"))
        # The same dept, sem and section may exist for another batch year, but not twice without one.
        self.client.post(
            reverse("section_create"), {"class_name": "B.Tech in CS 5th sem", "name": "K", "year": "2029"}
        )
        self.client.post(reverse("section_create"), {"class_name": "B.Tech in CS 5th sem", "name": "K"})
        response = self.client.post(
            reverse("section_create"), {"class_name": "B.Tech in CS 5th sem", "name": "K"}
        )
        self.assertContains(response, "That section already exists")
        self.assertEqual(Section.objects.filter(class_name="B.Tech in CS 5th sem").count(), 3)
        response = self.client.post(
            reverse("section_create"), {"class_name": "B.Tech in CS 5th sem", "name": "L", "year": "1999"}
        )
        self.assertContains(response, "Enter a year between 2000 and 2100")

    def test_admin_edits_section_year(self):
        self.client.force_login(self.admin)
        response = self.client.post(
            reverse("section_edit", args=[self.section_a.pk]),
            {"class_name": "B.Tech CSE Year 2", "name": "A", "year": "2028"},
        )
        self.assertRedirects(response, reverse("section_detail", args=[self.section_a.pk]))
        self.section_a.refresh_from_db()
        self.assertEqual(self.section_a.year, 2028)
        self.assertTrue(AuditEntry.objects.filter(action="section.update").exists())

    def test_unused_section_can_be_deleted_but_used_one_is_kept(self):
        self.client.force_login(self.admin)
        empty = Section.objects.create(class_name="Software Engineering", name="K")
        TeachingAssignment.objects.create(section=empty, subject=self.subject)
        response = self.client.post(reverse("section_delete", args=[empty.pk]))
        self.assertRedirects(response, reverse("section_list"))
        self.assertFalse(Section.objects.filter(pk=empty.pk).exists())
        self.assertTrue(AuditEntry.objects.filter(action="section.delete").exists())

        Enrollment.objects.create(student=self.student, assignment=self.assignment_a)
        response = self.client.post(reverse("section_delete", args=[self.section_a.pk]))
        self.assertContains(response, "cannot be deleted yet")
        self.assertTrue(Section.objects.filter(pk=self.section_a.pk).exists())

    def test_faculty_cannot_edit_or_delete_sections(self):
        self.client.force_login(self.faculty)
        for name in ("section_edit", "section_delete"):
            with self.subTest(name=name):
                self.assertEqual(self.client.post(reverse(name, args=[self.section_b.pk])).status_code, 403)
        self.assertTrue(Section.objects.filter(pk=self.section_b.pk).exists())

    def test_admin_enrolls_student_and_sees_roster(self):
        self.client.force_login(self.admin)
        response = self.client.post(
            reverse("enrollment_create", args=[self.section_a.pk]),
            {"student": self.student.pk, "assignment": self.assignment_a.pk},
        )
        self.assertRedirects(response, reverse("section_detail", args=[self.section_a.pk]))
        enrollment = Enrollment.objects.get(student=self.student)
        self.assertEqual((enrollment.subject, enrollment.assignment), (self.subject, self.assignment_a))
        roster = self.client.get(reverse("section_detail", args=[self.section_a.pk]))
        self.assertContains(roster, "21CS001")
        self.assertContains(roster, "CS101")
        self.assertTrue(AuditEntry.objects.filter(action="enrollment.create").exists())

    def test_second_section_for_same_subject_is_rejected_with_existing_section(self):
        Enrollment.objects.create(student=self.student, assignment=self.assignment_a)
        self.client.force_login(self.admin)
        response = self.client.post(
            reverse("enrollment_create", args=[self.section_b.pk]),
            {"student": self.student.pk, "assignment": self.assignment_b.pk},
        )
        self.assertContains(response, "already enrolled in CS101")
        self.assertContains(response, "B.Tech CSE Year 2 A")
        self.assertEqual(Enrollment.objects.count(), 1)

    def test_assignment_from_different_section_is_rejected(self):
        self.client.force_login(self.admin)
        response = self.client.post(
            reverse("enrollment_create", args=[self.section_a.pk]),
            {"student": self.student.pk, "assignment": self.assignment_b.pk},
        )
        self.assertContains(response, "Select a valid choice")
        self.assertFalse(Enrollment.objects.exists())

    def test_inactive_student_cannot_be_enrolled(self):
        self.student_user.is_active = False
        self.student_user.save(update_fields=["is_active"])
        self.client.force_login(self.admin)
        response = self.client.post(
            reverse("enrollment_create", args=[self.section_a.pk]),
            {"student": self.student.pk, "assignment": self.assignment_a.pk},
        )
        self.assertContains(response, "Select a valid choice")
        self.assertFalse(Enrollment.objects.exists())

    def test_admin_can_remove_enrollment_without_removing_student(self):
        enrollment = Enrollment.objects.create(student=self.student, assignment=self.assignment_a)
        session = AttendanceSession.objects.create(
            assignment=self.assignment_a, date=date(2026, 10, 20), period=1
        )
        record = AttendanceRecord.objects.create(session=session, student=self.student, status="P")
        self.client.force_login(self.admin)
        self.assertEqual(
            self.client.get(
                reverse("enrollment_remove", args=[self.section_a.pk, enrollment.pk])
            ).status_code,
            405,
        )
        response = self.client.post(reverse("enrollment_remove", args=[self.section_a.pk, enrollment.pk]))
        self.assertRedirects(response, reverse("section_detail", args=[self.section_a.pk]))
        self.assertFalse(Enrollment.objects.filter(pk=enrollment.pk).exists())
        self.assertTrue(Student.objects.filter(pk=self.student.pk).exists())
        self.assertTrue(AttendanceRecord.objects.filter(pk=record.pk).exists())
        self.assertTrue(AuditEntry.objects.filter(action="enrollment.remove").exists())

    def test_faculty_and_student_cannot_manage_sections_or_enrollment(self):
        for user in (self.faculty, self.student_user):
            with self.subTest(user=user):
                self.client.force_login(user)
                self.assertEqual(self.client.get(reverse("section_list")).status_code, 403)
                self.assertEqual(
                    self.client.post(
                        reverse("section_create"), {"class_name": "Unwanted", "name": "Z"}
                    ).status_code,
                    403,
                )
                self.assertEqual(
                    self.client.post(
                        reverse("enrollment_create", args=[self.section_a.pk]),
                        {"student": self.student.pk, "assignment": self.assignment_a.pk},
                    ).status_code,
                    403,
                )
        self.assertFalse(Section.objects.filter(class_name="Unwanted").exists())
        self.assertFalse(Enrollment.objects.exists())


class StudentListSubjectsTests(TestCase):
    def test_faculty_see_only_subjects_they_teach_each_student(self):
        teacher, other = make_faculty("F001"), make_faculty("F002")
        student = make_student("S001")
        section = Section.objects.create(class_name="B.Tech in CS 5th sem", name="K", year=2028)
        mine = TeachingAssignment.objects.create(
            section=section, subject=Subject.objects.create(code="CS101", name="Programming"), faculty=teacher
        )
        theirs = TeachingAssignment.objects.create(
            section=section, subject=Subject.objects.create(code="MA101", name="Mathematics"), faculty=other
        )
        for assignment in (mine, theirs):
            Enrollment.objects.create(student=student, assignment=assignment)

        self.client.force_login(teacher.user)
        response = self.client.get(reverse("student_list"))
        self.assertContains(response, "Class and section")
        self.assertContains(response, "CS101 – Programming")
        self.assertNotContains(response, "MA101")

        self.client.force_login(User.objects.create_user(username="ADMIN9", role=Role.ADMIN))
        response = self.client.get(reverse("student_list"))
        self.assertContains(response, "CS101 – Programming")
        self.assertContains(response, "MA101 – Mathematics")
