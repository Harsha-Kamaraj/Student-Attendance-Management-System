"""Error and repeat-request paths in student, faculty, section and subject management (Part 3 coverage)."""

from unittest.mock import patch

from django.db import IntegrityError
from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import Role, User
from apps.audit.models import AuditEntry

from .forms import (
    FacultyCreateForm,
    FacultyFieldsForm,
    SectionForm,
    StudentCreateForm,
    StudentFieldsForm,
    SubjectForm,
)
from .models import Enrollment, Faculty, Section, Student, Subject, TeachingAssignment
from .tests import make_faculty, make_student

PASSWORD = "Attend#2026"


class BlankFieldGuardTests(TestCase):
    """The web form rejects empty fields first; these clean methods are the backup guard behind it."""

    def check_guard(self, form_class, field, message, **form_kwargs):
        form = form_class(**form_kwargs)
        form.cleaned_data = {field: "   "}
        with self.assertRaisesMessage(Exception, message):
            getattr(form, f"clean_{field}")()

    def test_whitespace_only_values_are_rejected_by_each_clean_method(self):
        cases = [
            (StudentFieldsForm, "full_name", "Student name is required."),
            (SectionForm, "class_name", "Dept and sem is required."),
            (SectionForm, "name", "Section is required."),
            (SubjectForm, "name", "Subject name is required."),
            (FacultyFieldsForm, "full_name", "Faculty name is required."),
            (FacultyFieldsForm, "department", "Department is required."),
        ]
        for form_class, field, message in cases:
            with self.subTest(form=form_class.__name__, field=field):
                self.check_guard(form_class, field, message)


class LoginIdentifierFormatTests(TestCase):
    def setUp(self):
        self.section = Section.objects.create(class_name="B.Tech CSE Year 2", name="A")

    def test_roll_number_with_unsupported_characters_is_rejected(self):
        form = StudentCreateForm(
            data={
                "roll_number": "S#001",
                "full_name": "Asha",
                "class_name": "B.Tech CSE Year 2",
                "home_section": self.section.pk,
                "email": "asha@example.edu",
            }
        )
        self.assertFalse(form.is_valid())
        self.assertIn("Use letters, numbers or @ . + - _ only.", form.errors["roll_number"])

    def test_faculty_id_with_unsupported_characters_is_rejected(self):
        form = FacultyCreateForm(
            data={"faculty_id": "F 001", "full_name": "Ravi", "department": "CSE", "email": "r@example.edu"}
        )
        self.assertFalse(form.is_valid())
        self.assertIn("Use letters, numbers or @ . + - _ only.", form.errors["faculty_id"])


class AdminViewErrorPathTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(username="ADMIN1", password=PASSWORD, role=Role.ADMIN)
        self.client.force_login(self.admin)
        self.section = Section.objects.create(class_name="B.Tech CSE Year 2", name="A")
        self.subject = Subject.objects.create(code="CS101", name="Programming")
        self.student = make_student("S001")
        self.student.home_section = self.section
        self.student.save()
        self.member = make_faculty("F001")

    def test_invalid_edit_forms_show_the_page_again_and_change_nothing(self):
        cases = [
            ("student_edit", self.student.pk, {"full_name": "", "email": "bad"}),
            ("section_edit", self.section.pk, {"class_name": "B.Tech CSE Year 2", "name": ""}),
            ("subject_edit", self.subject.pk, {"name": ""}),
            ("faculty_edit", self.member.pk, {"full_name": "Faculty F001", "department": "", "email": "x"}),
        ]
        for name, pk, data in cases:
            with self.subTest(view=name):
                response = self.client.post(reverse(name, args=[pk]), data)
                self.assertEqual(response.status_code, 200)
                self.assertTrue(response.context["form"].errors)
        self.student.refresh_from_db()
        self.section.refresh_from_db()
        self.subject.refresh_from_db()
        self.member.refresh_from_db()
        self.assertEqual(self.student.full_name, "Student S001")
        self.assertEqual(self.section.name, "A")
        self.assertEqual(self.subject.name, "Programming")
        self.assertEqual(self.member.department, "CSE")
        self.assertFalse(AuditEntry.objects.filter(action__endswith=".update").exists())

    def test_repeating_deactivate_or_reactivate_changes_nothing_and_is_not_logged_again(self):
        self.student.user.is_active = False
        self.student.user.save()
        for name, pk in (
            ("student_deactivate", self.student.pk),
            ("student_reactivate", make_student("S002").pk),
            ("faculty_reactivate", self.member.pk),
        ):
            with self.subTest(view=name):
                response = self.client.post(reverse(name, args=[pk]))
                self.assertEqual(response.status_code, 302)
        self.assertFalse(
            AuditEntry.objects.filter(
                action__in=["student.deactivate", "student.reactivate", "faculty.reactivate"]
            ).exists()
        )

    def test_student_delete_page_asks_for_confirmation_before_deleting(self):
        response = self.client.get(reverse("student_delete", args=[self.student.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(Student.objects.filter(pk=self.student.pk).exists())


class ConcurrentDuplicateTests(TestCase):
    """Another Admin saving the same record first makes the database refuse the second save."""

    def setUp(self):
        self.admin = User.objects.create_user(username="ADMIN1", password=PASSWORD, role=Role.ADMIN)
        self.client.force_login(self.admin)
        self.section = Section.objects.create(class_name="B.Tech CSE Year 2", name="A")
        self.subject = Subject.objects.create(code="CS101", name="Programming")
        self.assignment = TeachingAssignment.objects.create(section=self.section, subject=self.subject)
        self.student = make_student("S001")
        self.member = make_faculty("F001")
        self.other_subject = Subject.objects.create(code="CS102", name="Data Structures")

    def assert_refused(self, response, message):
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, message)

    def test_section_create_and_edit_report_a_duplicate_saved_meanwhile(self):
        with patch.object(SectionForm, "save", side_effect=IntegrityError):
            created = self.client.post(
                reverse("section_create"), {"class_name": "B.Tech CSE Year 3", "name": "B"}
            )
            edited = self.client.post(
                reverse("section_edit", args=[self.section.pk]),
                {"class_name": "B.Tech CSE Year 2", "name": "Z"},
            )
        self.assert_refused(created, "That section already exists for this dept, sem and year.")
        self.assert_refused(edited, "That section already exists for this dept, sem and year.")
        self.assertFalse(AuditEntry.objects.filter(action__startswith="section.").exists())

    def test_enrollment_reports_a_conflict_saved_meanwhile(self):
        with patch.object(Enrollment.objects, "create", side_effect=IntegrityError):
            response = self.client.post(
                reverse("enrollment_create", args=[self.section.pk]),
                {"student": self.student.pk, "assignment": self.assignment.pk},
            )
        self.assert_refused(response, "A conflicting enrollment already exists. Reload the roster.")
        self.assertFalse(Enrollment.objects.exists())

    def test_subject_create_reports_a_code_saved_meanwhile(self):
        with patch.object(SubjectForm, "save", side_effect=IntegrityError):
            response = self.client.post(reverse("subject_create"), {"code": "CS200", "name": "Networks"})
        self.assert_refused(response, "A subject with this code already exists.")
        self.assertFalse(Subject.objects.filter(code="CS200").exists())

    def test_subject_offer_and_class_assign_report_an_offering_saved_meanwhile(self):
        other_section = Section.objects.create(class_name="B.Tech CSE Year 2", name="B")
        with patch.object(TeachingAssignment.objects, "create", side_effect=IntegrityError):
            offered = self.client.post(
                reverse("subject_offer", args=[self.other_subject.pk]), {"section": other_section.pk}
            )
            assigned = self.client.post(
                reverse("class_assign", args=[self.section.pk]),
                {"subject": self.other_subject.pk, "faculty": self.member.pk},
            )
        self.assert_refused(offered, "This subject is already offered in that section.")
        self.assert_refused(assigned, "This subject is already offered in this section.")
        self.assertEqual(TeachingAssignment.objects.count(), 1)
        self.assertFalse(Faculty.objects.filter(assignments__isnull=False).exists())
