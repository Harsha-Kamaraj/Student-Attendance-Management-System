"""BL-09 / UC-04: subject management."""

import datetime

from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import Role, User
from apps.attendance.models import AttendanceSession
from apps.audit.models import AuditEntry

from .models import Enrollment, Section, Subject, TeachingAssignment
from .tests import make_faculty, make_student

PASSWORD = "Attend#2026"


class SubjectTestBase(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(username="ADMIN1", password=PASSWORD, role=Role.ADMIN)
        self.faculty = make_faculty("F001")
        self.student = make_student("21CS001")
        self.section = Section.objects.create(class_name="B.Tech CSE Year 2", name="A")
        self.other_section = Section.objects.create(class_name="B.Tech CSE Year 2", name="B")
        self.cs101 = Subject.objects.create(code="CS101", name="Programming")
        self.cs102 = Subject.objects.create(code="CS102", name="Data Structures")
        # F001 teaches CS101 in section A.
        self.taught = TeachingAssignment.objects.create(
            section=self.section, subject=self.cs101, faculty=self.faculty
        )

    def login(self, username):
        self.client.logout()
        self.client.login(username=username, password=PASSWORD)


class CreateAndViewTests(SubjectTestBase):
    def test_admin_creates_subject_code_stored_in_capitals(self):
        # UT_04_1, AC 1
        self.login("ADMIN1")
        response = self.client.post(reverse("subject_create"), {"code": " ma201 ", "name": " Mathematics "})
        subject = Subject.objects.get(code="MA201")
        self.assertRedirects(response, reverse("subject_detail", args=[subject.pk]))
        self.assertEqual(subject.name, "Mathematics")
        entry = AuditEntry.objects.get(action="subject.create")
        self.assertEqual(entry.new_value, {"code": "MA201", "name": "Mathematics"})

    def test_faculty_can_create_subject(self):
        # FR-05
        self.login("F001")
        self.client.post(reverse("subject_create"), {"code": "PH101", "name": "Physics"})
        self.assertTrue(Subject.objects.filter(code="PH101").exists())

    def test_admin_and_faculty_see_the_list(self):
        for username in ("ADMIN1", "F001"):
            with self.subTest(user=username):
                self.login(username)
                response = self.client.get(reverse("subject_list"))
                self.assertContains(response, "CS101")
                self.assertContains(response, "CS102")

    def test_student_cannot_view_or_create_subjects(self):
        self.login("21CS001")
        self.assertEqual(self.client.get(reverse("subject_list")).status_code, 403)
        response = self.client.post(reverse("subject_create"), {"code": "XX1", "name": "Hack"})
        self.assertEqual(response.status_code, 403)
        self.assertFalse(Subject.objects.filter(code="XX1").exists())

    def test_duplicate_code_is_rejected_ignoring_case(self):
        # UT_04_3, ST_04_2, UC-04 3a
        self.login("ADMIN1")
        response = self.client.post(reverse("subject_create"), {"code": "cs101", "name": "Again"})
        self.assertContains(response, "A subject with this code already exists.")
        self.assertEqual(Subject.objects.filter(code__iexact="CS101").count(), 1)

    def test_missing_and_invalid_details_are_rejected(self):
        # UT_04_2, AC 2
        self.login("ADMIN1")
        blank = self.client.post(reverse("subject_create"), {"code": "", "name": "   "})
        self.assertContains(blank, "This field is required.")
        bad = self.client.post(reverse("subject_create"), {"code": "CS 1!", "name": "Bad"})
        self.assertContains(bad, "Use letters, digits and hyphens only.")
        self.assertEqual(Subject.objects.count(), 2)


class EditTests(SubjectTestBase):
    def test_admin_renames_subject_and_change_persists(self):
        # AC 4, IT_04_3
        self.login("ADMIN1")
        self.client.post(reverse("subject_edit", args=[self.cs102.pk]), {"name": "Data Structures I"})
        self.login("ADMIN1")
        self.assertContains(
            self.client.get(reverse("subject_detail", args=[self.cs102.pk])), "Data Structures I"
        )
        self.assertTrue(
            AuditEntry.objects.filter(action="subject.update", target_id=str(self.cs102.pk)).exists()
        )

    def test_code_cannot_be_changed(self):
        self.login("ADMIN1")
        self.client.post(
            reverse("subject_edit", args=[self.cs101.pk]), {"code": "ZZ999", "name": "Programming"}
        )
        self.cs101.refresh_from_db()
        self.assertEqual(self.cs101.code, "CS101")

    def test_faculty_edits_only_subjects_they_teach(self):
        # BL-05 decision
        self.login("F001")
        ok = self.client.post(reverse("subject_edit", args=[self.cs101.pk]), {"name": "Programming I"})
        self.assertRedirects(ok, reverse("subject_detail", args=[self.cs101.pk]))
        denied = self.client.post(reverse("subject_edit", args=[self.cs102.pk]), {"name": "Changed"})
        self.assertEqual(denied.status_code, 403)
        self.cs102.refresh_from_db()
        self.assertEqual(self.cs102.name, "Data Structures")

    def test_edit_link_shown_only_where_allowed(self):
        self.login("F001")
        response = self.client.get(reverse("subject_list"))
        self.assertContains(response, reverse("subject_edit", args=[self.cs101.pk]))
        self.assertNotContains(response, reverse("subject_edit", args=[self.cs102.pk]))


class OfferInSectionTests(SubjectTestBase):
    def test_admin_offers_subject_in_section_without_faculty_yet(self):
        # AC 3
        self.login("ADMIN1")
        self.client.post(reverse("subject_offer", args=[self.cs102.pk]), {"section": self.section.pk})
        assignment = TeachingAssignment.objects.get(section=self.section, subject=self.cs102)
        self.assertIsNone(assignment.faculty)
        self.assertTrue(AuditEntry.objects.filter(action="subject.offer").exists())

    def test_same_section_cannot_be_offered_twice(self):
        self.login("ADMIN1")
        response = self.client.post(
            reverse("subject_offer", args=[self.cs101.pk]), {"section": self.section.pk}
        )
        self.assertContains(response, "Select a valid choice")
        self.assertEqual(TeachingAssignment.objects.filter(subject=self.cs101).count(), 1)

    def test_faculty_cannot_offer_or_withdraw(self):
        self.login("F001")
        offer = self.client.post(reverse("subject_offer", args=[self.cs102.pk]), {"section": self.section.pk})
        withdraw = self.client.post(reverse("subject_withdraw", args=[self.cs101.pk, self.taught.pk]))
        self.assertEqual((offer.status_code, withdraw.status_code), (403, 403))
        self.assertFalse(TeachingAssignment.objects.filter(subject=self.cs102).exists())
        self.assertTrue(TeachingAssignment.objects.filter(pk=self.taught.pk).exists())

    def test_withdraw_unused_offering(self):
        self.login("ADMIN1")
        offering = TeachingAssignment.objects.create(section=self.other_section, subject=self.cs102)
        self.client.post(reverse("subject_withdraw", args=[self.cs102.pk, offering.pk]))
        self.assertFalse(TeachingAssignment.objects.filter(pk=offering.pk).exists())

    def test_withdraw_blocked_while_students_are_enrolled(self):
        Enrollment.objects.create(student=self.student, assignment=self.taught)
        self.login("ADMIN1")
        response = self.client.post(
            reverse("subject_withdraw", args=[self.cs101.pk, self.taught.pk]), follow=True
        )
        self.assertContains(response, "cannot be withdrawn")
        self.assertTrue(TeachingAssignment.objects.filter(pk=self.taught.pk).exists())

    def test_withdraw_blocked_when_attendance_exists(self):
        AttendanceSession.objects.create(assignment=self.taught, date=datetime.date(2026, 10, 6), period=1)
        self.login("ADMIN1")
        self.client.post(reverse("subject_withdraw", args=[self.cs101.pk, self.taught.pk]))
        self.assertTrue(TeachingAssignment.objects.filter(pk=self.taught.pk).exists())


class DeleteTests(SubjectTestBase):
    def test_only_admin_can_delete(self):
        self.login("F001")
        self.assertEqual(self.client.post(reverse("subject_delete", args=[self.cs102.pk])).status_code, 403)
        self.assertTrue(Subject.objects.filter(pk=self.cs102.pk).exists())

    def test_get_only_asks_for_confirmation(self):
        self.login("ADMIN1")
        response = self.client.get(reverse("subject_delete", args=[self.cs102.pk]))
        self.assertContains(response, "Confirm deletion")
        self.assertTrue(Subject.objects.filter(pk=self.cs102.pk).exists())

    def test_unused_subject_is_deleted_with_its_offerings(self):
        # FR-05 AC 3, ST_04_4
        offering = TeachingAssignment.objects.create(section=self.other_section, subject=self.cs102)
        self.login("ADMIN1")
        response = self.client.post(reverse("subject_delete", args=[self.cs102.pk]))
        self.assertRedirects(response, reverse("subject_list"))
        self.assertFalse(Subject.objects.filter(pk=self.cs102.pk).exists())
        self.assertFalse(TeachingAssignment.objects.filter(pk=offering.pk).exists())
        self.assertTrue(AuditEntry.objects.filter(action="subject.delete").exists())

    def test_subject_with_attendance_cannot_be_deleted(self):
        # AC 5, BL-01 D-05, ST_04_3
        AttendanceSession.objects.create(assignment=self.taught, date=datetime.date(2026, 10, 6), period=1)
        self.login("ADMIN1")
        response = self.client.post(reverse("subject_delete", args=[self.cs101.pk]))
        self.assertContains(response, "cannot be deleted")
        self.assertTrue(Subject.objects.filter(pk=self.cs101.pk).exists())

    def test_subject_with_enrolled_students_cannot_be_deleted(self):
        Enrollment.objects.create(student=self.student, assignment=self.taught)
        self.login("ADMIN1")
        self.client.post(reverse("subject_delete", args=[self.cs101.pk]))
        self.assertTrue(Subject.objects.filter(pk=self.cs101.pk).exists())
        self.assertTrue(Enrollment.objects.filter(student=self.student, subject=self.cs101).exists())
