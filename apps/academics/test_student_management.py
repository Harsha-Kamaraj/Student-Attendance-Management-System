"""UC-02: student management, lifecycle and scope protection (BL-07)."""

from datetime import date

from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import Role, User
from apps.attendance.models import AttendanceRecord, AttendanceSession
from apps.audit.models import AuditEntry

from .models import Enrollment, Faculty, Section, Student, Subject, TeachingAssignment

PASSWORD = "Attend#2026"


class StudentManagementTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(username="ADMIN1", password=PASSWORD, role=Role.ADMIN)
        self.faculty_user = User.objects.create_user(username="F001", password=PASSWORD, role=Role.FACULTY)
        self.faculty = Faculty.objects.create(
            user=self.faculty_user, faculty_id="F001", full_name="Teacher", department="CSE"
        )
        self.section_a = Section.objects.create(class_name="B.Tech CSE Year 2", name="A")
        self.section_b = Section.objects.create(class_name="B.Tech CSE Year 2", name="B")
        self.subject = Subject.objects.create(code="CS101", name="Programming")
        self.assignment = TeachingAssignment.objects.create(
            section=self.section_a, subject=self.subject, faculty=self.faculty
        )
        self.student_user = User.objects.create_user(username="21CS001", password=PASSWORD, role=Role.STUDENT)
        self.student = Student.objects.create(
            user=self.student_user,
            roll_number="21CS001",
            full_name="First Student",
            home_section=self.section_a,
        )
        Enrollment.objects.create(student=self.student, assignment=self.assignment)

    def form_data(self, **updates):
        return {
            "roll_number": "21cs002",
            "full_name": "Second Student",
            "class_name": self.section_b.class_name,
            "home_section": str(self.section_b.pk),
            "email": "second@example.edu",
            **updates,
        }

    def test_admin_creates_student_and_login_atomically(self):
        self.client.force_login(self.admin)
        response = self.client.post(reverse("student_create"), self.form_data())
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'data-testid="temporary-password"')
        student = Student.objects.get(roll_number="21CS002")
        self.assertEqual(student.user.username, "21CS002")
        self.assertTrue(student.user.must_change_password)
        self.assertEqual(student.home_section, self.section_b)
        self.assertIn("no-store", response["Cache-Control"])
        self.assertTrue(AuditEntry.objects.filter(action="student.create").exists())

    def test_required_class_section_and_name_are_validated(self):
        self.client.force_login(self.admin)
        invalid = self.form_data(full_name="", class_name="", home_section="")
        response = self.client.post(reverse("student_create"), invalid)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "This field is required.")
        self.assertFalse(Student.objects.filter(roll_number="21CS002").exists())

    def test_duplicate_roll_is_rejected_case_insensitively(self):
        self.client.force_login(self.admin)
        response = self.client.post(reverse("student_create"), self.form_data(roll_number="21cs001"))
        self.assertContains(response, "This roll number already exists.")
        self.assertEqual(Student.objects.count(), 1)

    def test_class_section_mismatch_is_rejected(self):
        other = Section.objects.create(class_name="B.Tech ECE Year 2", name="A")
        self.client.force_login(self.admin)
        response = self.client.post(reverse("student_create"), self.form_data(home_section=str(other.pk)))
        self.assertContains(response, "section must belong to the selected class")
        self.assertFalse(Student.objects.filter(roll_number="21CS002").exists())

    def test_admin_can_edit_student_and_changes_persist(self):
        self.client.force_login(self.admin)
        response = self.client.post(
            reverse("student_edit", args=[self.student.pk]),
            {
                "full_name": "Updated",
                "class_name": self.section_b.class_name,
                "home_section": str(self.section_b.pk),
                "email": "new@example.edu",
            },
        )
        self.assertRedirects(response, reverse("student_detail", args=[self.student.pk]))
        self.student.refresh_from_db()
        self.student_user.refresh_from_db()
        self.assertEqual((self.student.full_name, self.student.home_section), ("Updated", self.section_b))
        self.assertEqual(self.student_user.email, "new@example.edu")
        self.assertEqual(self.student.enrollments.count(), 1)  # Existing subject enrollment is preserved.

    def test_deactivate_and_reactivate_keep_attendance_history(self):
        self.client.force_login(self.admin)
        url = reverse("student_deactivate", args=[self.student.pk])
        self.assertEqual(self.client.get(url).status_code, 405)
        self.client.post(url)
        self.student_user.refresh_from_db()
        self.assertFalse(self.student_user.is_active)
        self.assertEqual(Enrollment.objects.filter(student=self.student).count(), 1)
        self.client.post(reverse("student_reactivate", args=[self.student.pk]))
        self.student_user.refresh_from_db()
        self.assertTrue(self.student_user.is_active)
        self.assertTrue(AuditEntry.objects.filter(action="student.deactivate").exists())
        self.assertTrue(AuditEntry.objects.filter(action="student.reactivate").exists())

    def test_delete_needs_reason_and_retains_audit(self):
        self.client.force_login(self.admin)
        url = reverse("student_delete", args=[self.student.pk])
        self.client.post(url, {"reason": " "})
        self.assertTrue(Student.objects.filter(pk=self.student.pk).exists())
        self.assertRedirects(self.client.post(url, {"reason": "Erroneous entry"}), reverse("student_list"))
        self.assertFalse(User.objects.filter(pk=self.student_user.pk).exists())
        self.assertEqual(AuditEntry.objects.get(action="student.delete").reason, "Erroneous entry")

    def test_deactivation_keeps_recorded_attendance(self):
        session = AttendanceSession.objects.create(
            assignment=self.assignment, date=date(2026, 10, 20), period=1
        )
        record = AttendanceRecord.objects.create(session=session, student=self.student, status="P")
        self.client.force_login(self.admin)
        self.client.post(reverse("student_deactivate", args=[self.student.pk]))
        self.assertTrue(AttendanceRecord.objects.filter(pk=record.pk).exists())
        self.client.post(reverse("student_reactivate", args=[self.student.pk]))
        self.assertTrue(AttendanceRecord.objects.filter(pk=record.pk).exists())

    def test_deletion_removes_attendance_but_keeps_audit(self):
        session = AttendanceSession.objects.create(
            assignment=self.assignment, date=date(2026, 10, 20), period=1
        )
        record = AttendanceRecord.objects.create(session=session, student=self.student, status="P")
        self.client.force_login(self.admin)
        self.client.post(reverse("student_delete", args=[self.student.pk]), {"reason": "Duplicate record"})
        self.assertFalse(AttendanceRecord.objects.filter(pk=record.pk).exists())
        self.assertTrue(AuditEntry.objects.filter(action="student.delete").exists())

    def test_faculty_scope_student_self_view_and_writes_denied(self):
        second_user = User.objects.create_user(username="21CS099", password=PASSWORD, role=Role.STUDENT)
        second = Student.objects.create(user=second_user, roll_number="21CS099", full_name="Outside")
        self.client.force_login(self.faculty_user)
        self.assertContains(self.client.get(reverse("student_list")), "21CS001")
        self.assertNotContains(self.client.get(reverse("student_list")), "21CS099")
        self.assertEqual(self.client.get(reverse("student_detail", args=[second.pk])).status_code, 403)
        self.assertEqual(self.client.post(reverse("student_create"), self.form_data()).status_code, 403)
        self.assertFalse(Student.objects.filter(roll_number="21CS002").exists())
        self.client.force_login(second_user)
        self.assertContains(self.client.get(reverse("student_detail", args=[second.pk])), "Outside")
        self.assertEqual(self.client.get(reverse("student_detail", args=[self.student.pk])).status_code, 403)
        denied = self.client.post(reverse("student_deactivate", args=[self.student.pk]))
        self.assertEqual(denied.status_code, 403)
