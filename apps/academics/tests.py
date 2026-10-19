from django.db import IntegrityError, transaction
from django.db.models import ProtectedError
from django.test import TestCase

from apps.accounts.models import Role, User

from .models import Enrollment, Faculty, Section, Student, Subject, TeachingAssignment


def make_student(roll):
    user = User.objects.create_user(username=roll, password="Attend#2026", role=Role.STUDENT)
    return Student.objects.create(user=user, roll_number=roll, full_name=f"Student {roll}")


def make_faculty(code):
    user = User.objects.create_user(username=code, password="Attend#2026", role=Role.FACULTY)
    return Faculty.objects.create(user=user, faculty_id=code, full_name=f"Faculty {code}", department="CSE")


class AcademicsTests(TestCase):
    def setUp(self):
        self.section_a = Section.objects.create(class_name="B.Tech CSE Year 2", name="A")
        self.section_b = Section.objects.create(class_name="B.Tech CSE Year 2", name="B")
        self.cs101 = Subject.objects.create(code="CS101", name="Programming")
        self.cs102 = Subject.objects.create(code="CS102", name="Data Structures")
        self.f1 = make_faculty("F001")
        self.a_cs101 = TeachingAssignment.objects.create(
            section=self.section_a, subject=self.cs101, faculty=self.f1
        )
        self.b_cs101 = TeachingAssignment.objects.create(section=self.section_b, subject=self.cs101)
        self.a_cs102 = TeachingAssignment.objects.create(section=self.section_a, subject=self.cs102)
        self.s1 = make_student("21CS001")

    def test_duplicate_roll_number_is_rejected(self):
        user = User.objects.create_user(username="other", password="Attend#2026", role=Role.STUDENT)
        with transaction.atomic(), self.assertRaises(IntegrityError):
            Student.objects.create(user=user, roll_number="21CS001", full_name="Duplicate")

    def test_duplicate_faculty_id_is_rejected(self):
        user = User.objects.create_user(username="other", password="Attend#2026", role=Role.FACULTY)
        with transaction.atomic(), self.assertRaises(IntegrityError):
            Faculty.objects.create(user=user, faculty_id="F001", full_name="Duplicate", department="CSE")

    def test_duplicate_subject_code_is_rejected(self):
        with transaction.atomic(), self.assertRaises(IntegrityError):
            Subject.objects.create(code="CS101", name="Duplicate")

    def test_duplicate_section_is_rejected(self):
        with transaction.atomic(), self.assertRaises(IntegrityError):
            Section.objects.create(class_name="B.Tech CSE Year 2", name="A")

    def test_subject_taught_once_per_section(self):
        with transaction.atomic(), self.assertRaises(IntegrityError):
            TeachingAssignment.objects.create(section=self.section_a, subject=self.cs101)

    def test_enrollment_fills_subject_from_assignment(self):
        enrollment = Enrollment.objects.create(student=self.s1, assignment=self.a_cs101)
        self.assertEqual(enrollment.subject, self.cs101)

    def test_student_can_take_different_subjects(self):
        Enrollment.objects.create(student=self.s1, assignment=self.a_cs101)
        Enrollment.objects.create(student=self.s1, assignment=self.a_cs102)
        self.assertEqual(self.s1.enrollments.count(), 2)

    def test_second_section_for_same_subject_is_rejected(self):
        # BL-01 D-19: one section per subject per student.
        Enrollment.objects.create(student=self.s1, assignment=self.a_cs101)
        with transaction.atomic(), self.assertRaises(IntegrityError):
            Enrollment.objects.create(student=self.s1, assignment=self.b_cs101)

    def test_faculty_with_assignments_cannot_be_deleted(self):
        # BL-01 D-04: reassign classes before deleting a faculty member.
        with self.assertRaises(ProtectedError):
            self.f1.user.delete()
        self.assertTrue(Faculty.objects.filter(pk=self.f1.pk).exists())

    def test_faculty_without_assignments_can_be_deleted(self):
        f2 = make_faculty("F002")
        f2.user.delete()
        self.assertFalse(Faculty.objects.filter(faculty_id="F002").exists())

    def test_subject_without_attendance_can_be_deleted(self):
        Enrollment.objects.create(student=self.s1, assignment=self.a_cs102)
        self.cs102.delete()
        self.assertFalse(TeachingAssignment.objects.filter(subject__code="CS102").exists())
        self.assertFalse(Enrollment.objects.filter(student=self.s1, subject__code="CS102").exists())

    def test_relationships_survive_reload(self):
        Enrollment.objects.create(student=self.s1, assignment=self.a_cs101)
        enrollment = Enrollment.objects.select_related(
            "student__user", "assignment__section", "assignment__subject", "assignment__faculty"
        ).get(student__roll_number="21CS001")
        self.assertEqual(enrollment.student.user.username, "21CS001")
        self.assertEqual(str(enrollment.assignment.section), "B.Tech CSE Year 2 A")
        self.assertEqual(enrollment.assignment.subject.code, "CS101")
        self.assertEqual(enrollment.assignment.faculty.faculty_id, "F001")
