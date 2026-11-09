"""Admin planning pages: the weekly timetable and semester class totals."""

from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import Role, User
from apps.audit.models import AuditEntry

from .models import Section, Subject, TeachingAssignment, TimetableSlot
from .tests import make_faculty


class PlanningTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = User.objects.create_user(username="ADMIN1", role=Role.ADMIN)
        cls.faculty = make_faculty("F001")
        cls.section_a = Section.objects.create(class_name="CSE", name="A")
        cls.section_b = Section.objects.create(class_name="CSE", name="B")
        cls.cs101 = Subject.objects.create(code="CS101", name="Programming")
        cls.ma101 = Subject.objects.create(code="MA101", name="Mathematics")
        cls.cs_a = TeachingAssignment.objects.create(
            section=cls.section_a, subject=cls.cs101, faculty=cls.faculty
        )
        cls.ma_a = TeachingAssignment.objects.create(section=cls.section_a, subject=cls.ma101)
        cls.cs_b = TeachingAssignment.objects.create(
            section=cls.section_b, subject=cls.cs101, faculty=cls.faculty
        )

    def setUp(self):
        self.client.force_login(self.admin)

    def add(self, assignment, weekday=0, period=1):
        return self.client.post(
            reverse("timetable"), {"assignment": assignment.pk, "weekday": weekday, "period": period}
        )

    def test_admin_adds_and_removes_timetable_classes(self):
        self.assertRedirects(self.add(self.cs_a), reverse("timetable"))
        slot = TimetableSlot.objects.get()
        self.assertContains(self.client.get(reverse("timetable")), "CS101 – Programming")
        self.assertTrue(AuditEntry.objects.filter(action="timetable.slot.add").exists())
        self.assertRedirects(
            self.client.post(reverse("timetable_remove", args=[slot.pk])), reverse("timetable")
        )
        self.assertFalse(TimetableSlot.objects.exists())
        self.assertTrue(AuditEntry.objects.filter(action="timetable.slot.remove").exists())

    def test_clashes_for_a_section_or_a_teacher_are_rejected(self):
        self.add(self.cs_a)
        section_clash = self.add(self.ma_a)
        self.assertContains(section_clash, "already has CS101 – Programming at that time", status_code=400)
        teacher_clash = self.add(self.cs_b)
        self.assertContains(teacher_clash, "already teaches CS101 – Programming", status_code=400)
        duplicate = self.add(self.cs_a)
        self.assertEqual(duplicate.status_code, 400)
        self.assertEqual(TimetableSlot.objects.count(), 1)

    def test_admin_sets_semester_class_totals(self):
        response = self.client.post(
            reverse("semester_plan"),
            {f"planned_{self.cs_a.pk}": "40", f"planned_{self.ma_a.pk}": "", f"planned_{self.cs_b.pk}": "36"},
        )
        self.assertRedirects(response, reverse("semester_plan"))
        self.cs_a.refresh_from_db()
        self.assertEqual(self.cs_a.planned_sessions, 40)
        self.assertEqual(AuditEntry.objects.filter(action="semester_plan.update").count(), 2)

    def test_invalid_semester_totals_save_nothing(self):
        response = self.client.post(
            reverse("semester_plan"), {f"planned_{self.cs_a.pk}": "40", f"planned_{self.ma_a.pk}": "abc"}
        )
        self.assertContains(response, "Enter a whole number from 1 to 500", status_code=400)
        self.cs_a.refresh_from_db()
        self.assertIsNone(self.cs_a.planned_sessions)

    def test_only_the_admin_can_open_the_planning_pages(self):
        self.client.force_login(self.faculty.user)
        for name in ("timetable", "semester_plan"):
            with self.subTest(page=name):
                self.assertEqual(self.client.get(reverse(name)).status_code, 403)
