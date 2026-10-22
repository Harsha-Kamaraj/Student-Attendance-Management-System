"""BL-12 (UT_06 / IT_06 / ST_06): end-to-end attendance marking."""

from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.academics.models import Enrollment, Faculty, Section, Student, Subject, TeachingAssignment
from apps.accounts.models import Role, User

from .models import AttendanceRecord, AttendanceSession, Status


class MarkingTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.faculty_user = User.objects.create_user(
            username="F001", password="Attend#2026", role=Role.FACULTY
        )
        cls.other_user = User.objects.create_user(username="F002", password="Attend#2026", role=Role.FACULTY)
        cls.admin = User.objects.create_user(username="ADMIN1", password="Attend#2026", role=Role.ADMIN)
        cls.faculty = Faculty.objects.create(
            user=cls.faculty_user, faculty_id="F001", full_name="Teacher One", department="CSE"
        )
        other_faculty = Faculty.objects.create(
            user=cls.other_user, faculty_id="F002", full_name="Teacher Two", department="CSE"
        )
        section = Section.objects.create(class_name="CSE Year 2", name="A")
        cls.subject = Subject.objects.create(code="CS101", name="Programming")
        cls.assignment = TeachingAssignment.objects.create(
            section=section, subject=cls.subject, faculty=cls.faculty
        )
        cls.other_assignment = TeachingAssignment.objects.create(
            section=Section.objects.create(class_name="CSE Year 2", name="B"),
            subject=cls.subject,
            faculty=other_faculty,
        )
        cls.students = []
        for roll in ("21CS001", "21CS002"):
            user = User.objects.create_user(username=roll, password="Attend#2026", role=Role.STUDENT)
            student = Student.objects.create(user=user, roll_number=roll, full_name=f"Student {roll}")
            Enrollment.objects.create(student=student, assignment=cls.assignment)
            cls.students.append(student)
        cls.day = timezone.localdate() - timedelta(days=1)

    def payload(self, **overrides):
        values = {
            "assignment": str(self.assignment.pk),
            "date": self.day.isoformat(),
            "period": "1",
            f"status_{self.students[0].pk}": "P",
            f"status_{self.students[1].pk}": "A",
        }
        values.update(overrides)
        return values

    def test_faculty_sees_only_assigned_classes(self):
        self.client.force_login(self.faculty_user)
        response = self.client.get(reverse("attendance_mark"))
        self.assertContains(response, str(self.assignment))
        self.assertNotContains(response, str(self.other_assignment))

    def test_correct_active_roster_is_displayed(self):
        self.client.force_login(self.faculty_user)
        response = self.client.get(reverse("attendance_mark"), self.payload())
        self.assertEqual(response.status_code, 200)
        for student in self.students:
            self.assertContains(response, student.roll_number)
        self.assertContains(response, "Mark remaining as Present")
        self.assertContains(response, "No default is applied automatically")

    def test_saves_all_records_and_survives_relogin(self):
        self.client.force_login(self.faculty_user)
        response = self.client.post(reverse("attendance_mark"), self.payload())
        self.assertEqual(response.status_code, 302)
        session = AttendanceSession.objects.get(assignment=self.assignment, date=self.day, period=1)
        self.assertEqual(session.records.count(), 2)
        self.assertEqual(
            list(session.records.order_by("student__roll_number").values_list("status", flat=True)),
            [Status.PRESENT, Status.ABSENT],
        )
        self.client.logout()
        self.client.force_login(self.faculty_user)
        response = self.client.get(reverse("attendance_mark"), self.payload())
        self.assertContains(response, "already saved")
        self.assertContains(response, "Absent")

    def test_missing_student_is_rejected_without_partial_save(self):
        self.client.force_login(self.faculty_user)
        data = self.payload()
        data.pop(f"status_{self.students[1].pk}")
        response = self.client.post(reverse("attendance_mark"), data)
        self.assertEqual(response.status_code, 400)
        self.assertContains(response, "Mark every enrolled student", status_code=400)
        self.assertFalse(AttendanceSession.objects.exists())
        self.assertFalse(AttendanceRecord.objects.exists())

    def test_invalid_status_is_rejected(self):
        self.client.force_login(self.faculty_user)
        response = self.client.post(
            reverse("attendance_mark"), self.payload(**{f"status_{self.students[1].pk}": "L"})
        )
        self.assertEqual(response.status_code, 400)
        self.assertFalse(AttendanceSession.objects.exists())

    def test_unassigned_class_is_forbidden(self):
        self.client.force_login(self.faculty_user)
        response = self.client.post(
            reverse("attendance_mark"), self.payload(assignment=str(self.other_assignment.pk))
        )
        self.assertEqual(response.status_code, 403)
        self.assertFalse(AttendanceSession.objects.exists())

    def test_student_cannot_mark_attendance(self):
        self.client.force_login(self.students[0].user)
        self.assertEqual(self.client.post(reverse("attendance_mark"), self.payload()).status_code, 403)

    def test_future_day_rejected(self):
        self.client.force_login(self.faculty_user)
        response = self.client.post(
            reverse("attendance_mark"),
            self.payload(date=(timezone.localdate() + timedelta(days=1)).isoformat()),
        )
        self.assertEqual(response.status_code, 400)
        self.assertFalse(AttendanceSession.objects.exists())

    def test_admin_must_supply_reason(self):
        self.client.force_login(self.admin)
        self.assertEqual(self.client.post(reverse("attendance_mark"), self.payload()).status_code, 400)
        self.assertFalse(AttendanceSession.objects.exists())
        response = self.client.post(reverse("attendance_mark"), self.payload(reason="Missed class"))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(AttendanceSession.objects.count(), 1)

    def test_inactive_students_are_not_in_new_rosters(self):
        self.students[1].user.is_active = False
        self.students[1].user.save(update_fields=["is_active"])
        self.client.force_login(self.faculty_user)
        response = self.client.post(reverse("attendance_mark"), self.payload())
        self.assertEqual(response.status_code, 400)
        self.assertFalse(AttendanceSession.objects.exists())
        data = self.payload()
        data.pop(f"status_{self.students[1].pk}")
        self.assertEqual(self.client.post(reverse("attendance_mark"), data).status_code, 302)
        self.assertEqual(AttendanceRecord.objects.count(), 1)
