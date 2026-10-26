"""Scoped, persistent attendance and correction history (BL-16 / BL-18)."""

from datetime import date, timedelta
from zoneinfo import ZoneInfo

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.academics.models import Enrollment, Section, Subject, TeachingAssignment
from apps.academics.tests import make_faculty, make_student
from apps.accounts.models import Role, User
from apps.audit.models import AuditEntry

from .models import AttendanceRecord, AttendanceSession, Status


class AttendanceHistoryTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = User.objects.create_user(username="ADMIN", password="Attend#2026", role=Role.ADMIN)
        cls.faculty = make_faculty("F001")
        cls.other_faculty = make_faculty("F002")
        cls.student = make_student("21CS001")
        cls.other_student = make_student("21CS002")
        cls.subject = Subject.objects.create(code="CS101", name="Programming")
        cls.other_subject = Subject.objects.create(code="CS102", name="Networks")
        cls.assignment = TeachingAssignment.objects.create(
            section=Section.objects.create(class_name="CSE Year 2", name="A"),
            subject=cls.subject,
            faculty=cls.faculty,
        )
        cls.other_assignment = TeachingAssignment.objects.create(
            section=Section.objects.create(class_name="CSE Year 2", name="B"),
            subject=cls.other_subject,
            faculty=cls.other_faculty,
        )
        Enrollment.objects.create(student=cls.student, assignment=cls.assignment)
        Enrollment.objects.create(student=cls.other_student, assignment=cls.other_assignment)
        cls.record = cls.create_record(cls.assignment, cls.student, date(2026, 10, 20), 1, Status.ABSENT)
        cls.later_record = cls.create_record(
            cls.assignment, cls.student, date(2026, 10, 21), 2, Status.PRESENT
        )
        cls.foreign_record = cls.create_record(
            cls.other_assignment, cls.other_student, date(2026, 10, 20), 1, Status.PRESENT
        )

    @staticmethod
    def create_record(assignment, student, day, period, status):
        session = AttendanceSession.objects.create(
            assignment=assignment,
            date=day,
            period=period,
            recorded_by=assignment.faculty.user,
            recorded_by_code=assignment.faculty.faculty_id,
        )
        return AttendanceRecord.objects.create(session=session, student=student, status=status)

    def history(self, params=None):
        return self.client.get(reverse("attendance_history"), params or {})

    def changes(self, record=None, params=None):
        return self.client.get(reverse("attendance_changes", args=[(record or self.record).pk]), params or {})

    def add_correction(self, record=None, **overrides):
        values = {
            "action": "attendance.correct",
            "actor_user_id": self.faculty.user_id,
            "actor_username": self.faculty.faculty_id,
            "target_type": "AttendanceRecord",
            "target_id": str((record or self.record).pk),
            "old_value": {"status": Status.ABSENT},
            "new_value": {"status": Status.PRESENT},
            "reason": "Corrected after checking the register",
        }
        return AuditEntry.objects.create(**(values | overrides))

    def test_login_is_required_for_both_history_pages(self):
        for response in (self.history(), self.changes()):
            self.assertEqual(response.status_code, 302)
            self.assertIn(reverse("login"), response.url)

    def test_students_cannot_open_history_including_their_own_changes(self):
        self.client.force_login(self.student.user)
        for response in (self.history(), self.changes()):
            self.assertEqual(response.status_code, 403)
            self.assertNotContains(response, self.student.full_name, status_code=403)
        self.assertEqual(AuditEntry.objects.filter(action="access.denied").count(), 2)

    def test_faculty_sees_only_assigned_records_and_filter_choices(self):
        self.client.force_login(self.faculty.user)
        response = self.history()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            {row.pk for row in response.context["page_obj"]}, {self.record.pk, self.later_record.pk}
        )
        self.assertContains(response, self.student.roll_number)
        self.assertNotContains(response, self.other_student.roll_number)
        self.assertNotContains(response, self.other_subject.code)
        self.assertContains(response, reverse("attendance_correct", args=[self.record.pk]))
        self.assertContains(response, reverse("attendance_changes", args=[self.record.pk]))
        self.assertIn("no-store", response["Cache-Control"])

    def test_admin_sees_all_records(self):
        self.client.force_login(self.admin)
        response = self.history()
        self.assertEqual(response.context["page_obj"].paginator.count, 3)
        self.assertContains(response, self.student.roll_number)
        self.assertContains(response, self.other_student.roll_number)

    def test_record_details_include_status_subject_class_and_original_recorder(self):
        self.client.force_login(self.faculty.user)
        response = self.history({"period": 1})
        for expected in ("21CS001", "CS101", "Programming", "CSE Year 2 A", "20 Oct 2026", "Absent", "F001"):
            self.assertContains(response, expected)

    def test_filter_dates_are_inclusive_and_filters_combine(self):
        self.client.force_login(self.faculty.user)
        response = self.history(
            {
                "assignment": self.assignment.pk,
                "student": self.student.pk,
                "start_date": "2026-10-20",
                "end_date": "2026-10-20",
                "period": 1,
                "status": Status.ABSENT,
            }
        )
        self.assertEqual([row.pk for row in response.context["page_obj"]], [self.record.pk])

    def test_each_optional_filter_narrows_records(self):
        self.client.force_login(self.faculty.user)
        cases = [
            ({"start_date": "2026-10-21"}, [self.later_record.pk]),
            ({"end_date": "2026-10-20"}, [self.record.pk]),
            ({"period": 2}, [self.later_record.pk]),
            ({"status": "A"}, [self.record.pk]),
        ]
        for filters, expected in cases:
            with self.subTest(filters=filters):
                self.assertEqual([row.pk for row in self.history(filters).context["page_obj"]], expected)

    def test_invalid_filters_show_errors_without_returning_unfiltered_records(self):
        self.client.force_login(self.faculty.user)
        for filters in (
            {"start_date": "invalid"},
            {"start_date": "2026-10-22", "end_date": "2026-10-20"},
            {"period": 0},
            {"period": 7},
            {"status": "L"},
            {"assignment": "invalid"},
            {"student": "999999999999999999999999999999999"},
        ):
            with self.subTest(filters=filters):
                response = self.history(filters)
                self.assertEqual(response.status_code, 200)
                self.assertTrue(response.context["form"].errors)
                self.assertEqual(list(response.context["page_obj"]), [])

    def test_foreign_filter_ids_return_logged_403_without_leaking_rows(self):
        self.client.force_login(self.faculty.user)
        for filters in ({"assignment": self.other_assignment.pk}, {"student": self.other_student.pk}):
            with self.subTest(filters=filters):
                response = self.history(filters)
                self.assertEqual(response.status_code, 403)
                self.assertNotContains(response, self.other_student.roll_number, status_code=403)
        self.assertEqual(AuditEntry.objects.filter(action="access.denied").count(), 2)

    def test_missing_filter_id_returns_404(self):
        self.client.force_login(self.faculty.user)
        self.assertEqual(self.history({"assignment": 999999}).status_code, 404)
        self.assertEqual(self.history({"student": 999999}).status_code, 404)

    def test_student_remains_visible_after_enrollment_is_removed(self):
        self.student.enrollments.all().delete()
        self.client.force_login(self.faculty.user)
        response = self.history({"student": self.student.pk})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["page_obj"].paginator.count, 2)
        self.assertContains(response, self.student.roll_number)

    def test_inactive_students_are_labelled_without_losing_history(self):
        self.student.user.is_active = False
        self.student.user.save(update_fields=["is_active"])
        self.client.force_login(self.faculty.user)
        self.assertContains(self.history(), "Inactive")
        self.assertContains(self.changes(), "Inactive")

    def test_original_recorder_code_survives_deleted_recorder(self):
        recorder = make_faculty("F009")
        AttendanceSession.objects.filter(pk=self.record.session_id).update(
            recorded_by=recorder.user, recorded_by_code="F009"
        )
        recorder.user.delete()
        self.client.force_login(self.faculty.user)
        self.assertContains(self.history(), "F009")
        self.assertContains(self.changes(), "F009")

    def test_empty_history_has_clear_message(self):
        self.client.force_login(self.faculty.user)
        self.assertContains(
            self.history({"start_date": "2030-01-01"}), "No attendance records match these filters"
        )

    def test_records_are_paginated_and_keep_filters_in_links(self):
        for number in range(26):
            self.create_record(
                self.assignment, self.student, date(2026, 8, 1) + timedelta(days=number), 1, Status.ABSENT
            )
        self.client.force_login(self.faculty.user)
        response = self.history({"status": "A", "page": 1})
        self.assertEqual(len(response.context["page_obj"]), 25)
        self.assertContains(response, "?status=A&amp;page=2")
        response = self.history({"status": "A", "page": 2})
        self.assertEqual(len(response.context["page_obj"]), 2)
        self.assertEqual(response.context["page_obj"].number, 2)

    def test_correction_history_is_for_the_exact_record_and_excludes_other_audit_actions(self):
        own = self.add_correction()
        self.add_correction(self.foreign_record, reason="FOREIGN RECORD SECRET")
        self.add_correction(action="password.change", reason="UNRELATED ACTION SECRET")
        self.add_correction(target_type="Student", reason="UNRELATED TARGET SECRET")
        for user in (self.faculty.user, self.admin):
            with self.subTest(user=user):
                self.client.force_login(user)
                response = self.changes()
                self.assertEqual([row.pk for row in response.context["page_obj"]], [own.pk])
                self.assertNotContains(response, "SECRET")

    def test_correction_history_shows_editor_time_statuses_reason_and_admin_override(self):
        correction = self.add_correction(
            actor_username=self.admin.username,
            is_admin_override=True,
            reason="Checked the signed register",
        )
        self.client.force_login(self.faculty.user)
        with timezone.override("UTC"):
            response = self.changes()
        for expected in ("Absent", "Present", "ADMIN", "Checked the signed register", "Yes"):
            self.assertContains(response, expected)
        displayed_time = correction.timestamp.astimezone(ZoneInfo("Asia/Kolkata")).strftime(
            "%d %b %Y %H:%M:%S"
        )
        self.assertContains(response, displayed_time)
        self.assertIn("no-store", response["Cache-Control"])

    def test_foreign_record_changes_return_logged_403_and_missing_record_returns_404(self):
        self.client.force_login(self.faculty.user)
        self.assertEqual(self.changes(self.foreign_record).status_code, 403)
        self.assertTrue(AuditEntry.objects.filter(action="access.denied").exists())
        self.assertEqual(self.client.get(reverse("attendance_changes", args=[999999])).status_code, 404)

    def test_reassignment_updates_history_scope_immediately(self):
        self.client.force_login(self.faculty.user)
        self.assignment.faculty = self.other_faculty
        self.assignment.save(update_fields=["faculty"])
        self.assertEqual(self.history().context["page_obj"].paginator.count, 0)
        self.assertEqual(self.changes().status_code, 403)

    def test_current_status_and_corrections_persist_after_relogin(self):
        self.add_correction()
        AttendanceRecord.objects.filter(pk=self.record.pk).update(status=Status.PRESENT)
        self.client.force_login(self.faculty.user)
        self.client.logout()
        self.client.force_login(self.faculty.user)
        response = self.history({"start_date": "2026-10-20", "end_date": "2026-10-20"})
        self.assertEqual(response.context["page_obj"][0].status, Status.PRESENT)
        self.assertContains(self.changes(), "Corrected after checking the register")

    def test_no_corrections_has_clear_empty_state(self):
        self.client.force_login(self.faculty.user)
        self.assertContains(self.changes(), "No corrections have been recorded")

    def test_corrections_are_paginated_latest_first(self):
        entries = [self.add_correction(reason=f"Reason {number}") for number in range(26)]
        self.client.force_login(self.faculty.user)
        response = self.changes()
        self.assertEqual(len(response.context["page_obj"]), 25)
        self.assertEqual(response.context["page_obj"][0].pk, entries[-1].pk)
        self.assertContains(response, "?page=2")
        response = self.changes(params={"page": 2})
        self.assertEqual([entry.pk for entry in response.context["page_obj"]], [entries[0].pk])

    def test_history_pages_reject_writes_and_do_not_change_records_or_audit(self):
        self.client.force_login(self.faculty.user)
        audit_count = AuditEntry.objects.count()
        self.assertEqual(self.client.post(reverse("attendance_history"), {"status": "P"}).status_code, 405)
        self.assertEqual(
            self.client.post(
                reverse("attendance_changes", args=[self.record.pk]), {"status": "P"}
            ).status_code,
            405,
        )
        self.assertEqual(AuditEntry.objects.count(), audit_count)
        self.record.refresh_from_db()
        self.assertEqual(self.record.status, Status.ABSENT)
