"""BL-23 (low-attendance notifications) and BL-24 (below-threshold list and Monday email).

Test IDs refer to the UC-10 group in Documents/Test_Plan_Document.docx.
"""

import datetime
from io import StringIO
from smtplib import SMTPException
from unittest import mock

from django.core import mail
from django.core.exceptions import PermissionDenied
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.academics.models import Enrollment, Section, Subject, TeachingAssignment
from apps.academics.tests import make_faculty, make_student
from apps.accounts.models import Role, User
from apps.attendance.corrections import correct_attendance
from apps.attendance.models import AttendanceRecord, AttendanceSession, AttendanceThreshold, Status
from apps.attendance.services import submit_attendance
from apps.audit.models import AuditEntry

from .models import Notification, ShortageFlag, WeeklyShortageEmail
from .services import (
    evaluate_students,
    is_below,
    send_weekly_faculty_emails,
    shortage_list_for,
    students_below,
)

P, A = Status.PRESENT, Status.ABSENT
HISTORY_START = datetime.date(2025, 1, 1)
MONDAY = datetime.datetime(2026, 11, 2, 8, 0, tzinfo=datetime.UTC)  # 13:30 IST, a Monday


class UnitRuleTests(TestCase):
    """UT_10_1 to UT_10_8: exact comparison, equality, zero classes, subject vs overall."""

    def test_exact_comparison(self):
        self.assertTrue(is_below(74, 99, 75))  # UT_10_1 / UT_10_4: 74.75%
        self.assertFalse(is_below(3, 4, 75))  # UT_10_5: equal is not flagged
        self.assertFalse(is_below(0, 0, 75))  # UT_10_6: no classes
        self.assertTrue(is_below(14_999, 20_000, 75))  # UT_10_7: shows 75.00% but is below
        self.assertTrue(is_below(74, 100, 75))
        self.assertFalse(is_below(75, 100, 75))
        self.assertFalse(is_below(76, 100, 75))  # UT_10_2


class Fixture(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = User.objects.create_user(
            username="ADMIN1", password="Attend#2026", role=Role.ADMIN, email="admin@example.edu"
        )
        cls.f1 = make_faculty("F001")
        cls.f2 = make_faculty("F002")
        cls.f3 = make_faculty("F003")
        for member in (cls.f1, cls.f2, cls.f3):
            member.user.email = f"{member.faculty_id.lower()}@example.edu"
            member.user.save(update_fields=["email"])
        cls.s1 = make_student("S001")
        cls.s2 = make_student("S002")
        for student in (cls.s1, cls.s2):
            student.user.email = f"{student.roll_number.lower()}@example.edu"
            student.user.save(update_fields=["email"])
        cls.section = Section.objects.create(class_name="B.Tech CSE Year 2", name="A")
        cls.cs101 = Subject.objects.create(code="CS101", name="Programming")
        cls.cs102 = Subject.objects.create(code="CS102", name="Data Structures")
        cls.cs103 = Subject.objects.create(code="CS103", name="No sessions yet")
        cls.a101 = TeachingAssignment.objects.create(section=cls.section, subject=cls.cs101, faculty=cls.f1)
        cls.a102 = TeachingAssignment.objects.create(section=cls.section, subject=cls.cs102, faculty=cls.f2)
        cls.a103 = TeachingAssignment.objects.create(section=cls.section, subject=cls.cs103, faculty=cls.f3)
        for student in (cls.s1, cls.s2):
            for assignment in (cls.a101, cls.a102, cls.a103):
                Enrollment.objects.create(student=student, assignment=assignment)

    def setUp(self):
        self.period = 0

    def history(self, student, assignment, attended, held):
        """Past records for one student, inserted directly (outside any notification path)."""
        for i in range(held):
            session, _ = AttendanceSession.objects.get_or_create(
                assignment=assignment,
                date=HISTORY_START + datetime.timedelta(days=i // 6),
                period=i % 6 + 1,
            )
            AttendanceRecord.objects.create(session=session, student=student, status=P if i < attended else A)

    def mark(self, assignment, faculty=None, **statuses):
        """Submit today's session through the real service; unnamed students are Present."""
        self.period += 1
        values = {
            e.student_id: statuses.get(e.student.roll_number, P)
            for e in Enrollment.objects.filter(assignment=assignment).select_related("student")
        }
        with self.captureOnCommitCallbacks(execute=True):
            submit_attendance(
                actor=(faculty or assignment.faculty).user,
                assignment=assignment,
                day=timezone.localdate(),
                period=self.period,
                statuses=values,
            )

    def notes(self, student):
        return list(Notification.objects.filter(recipient=student.user))


class DetectionTests(Fixture):
    def test_ut_10_2_below_at_and_above_and_zero(self):
        s3 = make_student("S003")
        s4 = make_student("S004")
        Enrollment.objects.create(student=s3, assignment=self.a101)
        self.history(self.s1, self.a101, 74, 100)
        self.history(self.s2, self.a101, 75, 100)
        self.history(s4, self.a101, 76, 100)
        below = students_below([self.s1.pk, self.s2.pk, s3.pk, s4.pk], 75)
        self.assertEqual(set(below), {self.s1.pk})

    def test_ut_10_8_subject_and_overall_evaluated_separately(self):
        self.history(self.s1, self.a101, 10, 10)
        self.history(self.s1, self.a102, 2, 3)
        below = students_below([self.s1.pk], 75)
        self.assertEqual(set(below[self.s1.pk]), {self.cs102.pk})  # subject B only; overall 12/13


class StudentNotificationTests(Fixture):
    def test_st_10_1_equal_is_silent_then_one_drop_one_notification_and_email(self):
        self.history(self.s1, self.a101, 75, 99)
        self.mark(self.a101, S001=A)  # 75/100 = 75.00%: equal, not flagged
        self.assertEqual(self.notes(self.s1), [])
        self.assertEqual(len(mail.outbox), 0)

        self.mark(self.a101, S001=A)  # 75/101 = 74.26%
        notes = self.notes(self.s1)
        self.assertEqual(len(notes), 1)
        self.assertIn("CS101 – Programming: 75/101 (74.26%)", notes[0].body)
        self.assertIn("Overall attendance: 75/101 (74.26%)", notes[0].body)
        self.assertIn("75%", notes[0].title)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["s001@example.edu"])
        self.assertEqual(mail.outbox[0].body, notes[0].body)
        # Only the affected student is told (SEC-25).
        self.assertEqual(Notification.objects.exclude(recipient=self.s1.user).count(), 0)
        self.assertEqual(self.notes(self.s2), [])

    def test_st_10_3_no_repeat_while_below(self):
        self.history(self.s1, self.a101, 74, 98)
        self.mark(self.a101, S001=A)  # 74/99: newly below
        self.mark(self.a101, S001=A)
        self.mark(self.a101, S001=A)  # 74/101: still below
        self.assertEqual(len(self.notes(self.s1)), 1)
        self.assertEqual(len(mail.outbox), 1)

    def test_st_10_2_and_st_10_4_recovery_clears_flag_and_next_drop_notifies_again(self):
        self.history(self.s1, self.a101, 74, 98)
        self.mark(self.a101, S001=A)  # 74/99
        self.assertTrue(ShortageFlag.objects.filter(student=self.s1, subject=self.cs101).exists())
        for _ in range(3):
            self.mark(self.a101)  # 77/102 = 75.49%
        self.assertFalse(ShortageFlag.objects.filter(student=self.s1).exists())
        self.assertEqual(len(self.notes(self.s1)), 1)  # no notification on recovery
        _, rows = shortage_list_for(self.admin)
        self.assertEqual(rows, [])  # recovered students leave the list (BL-24)

        self.mark(self.a101, S001=A)  # 77/103 = 74.76%
        self.assertEqual(len(self.notes(self.s1)), 2)
        self.assertEqual(len(mail.outbox), 2)

    def test_new_subject_drop_while_overall_already_below_notifies_once_for_that_subject(self):
        self.history(self.s1, self.a101, 1, 4)  # CS101 and overall below
        self.history(self.s1, self.a102, 3, 3)
        with self.captureOnCommitCallbacks(execute=True):
            evaluate_students([self.s1.pk])
        self.assertEqual(len(self.notes(self.s1)), 1)
        self.mark(self.a102, S001=A)
        self.mark(self.a102, S001=A)  # CS102 3/5 newly below; overall still below
        notes = self.notes(self.s1)
        self.assertEqual(len(notes), 2)
        self.assertIn("CS102", notes[0].body)
        self.assertNotIn("Overall", notes[0].body)

    def test_ut_10_6_subject_without_sessions_is_never_flagged(self):
        self.history(self.s1, self.a101, 1, 4)
        self.mark(self.a101)
        self.assertFalse(ShortageFlag.objects.filter(subject=self.cs103).exists())

    def test_it_10_6_correction_recovers_then_threshold_change_flags_again(self):
        self.history(self.s1, self.a101, 74, 100)
        with self.captureOnCommitCallbacks(execute=True):
            evaluate_students()
        self.assertEqual(len(self.notes(self.s1)), 1)
        record = AttendanceRecord.objects.filter(student=self.s1, status=A).order_by("pk").last()
        record.session.date = timezone.localdate()
        record.session.save(update_fields=["date"])
        with self.captureOnCommitCallbacks(execute=True):
            correct_attendance(actor=self.f1.user, record=record, status=P)  # 75/100
        self.assertFalse(ShortageFlag.objects.filter(student=self.s1).exists())

        self.client.force_login(self.admin)
        with self.captureOnCommitCallbacks(execute=True):
            self.client.post(reverse("threshold_settings"), {"value": 76})
        self.assertEqual(len(self.notes(self.s1)), 2)

    def test_it_10_4_threshold_change_re_evaluates_everyone_once(self):
        self.history(self.s1, self.a101, 78, 100)
        self.history(self.s2, self.a101, 85, 100)
        self.client.force_login(self.admin)
        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(reverse("threshold_settings"), {"value": 80})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(AttendanceThreshold.current_value(), 80)
        self.assertEqual(len(self.notes(self.s1)), 1)
        self.assertEqual(self.notes(self.s2), [])
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("80%", self.notes(self.s1)[0].body)

        with self.captureOnCommitCallbacks(execute=True):
            self.client.post(reverse("threshold_settings"), {"value": 80})
        self.assertEqual(len(self.notes(self.s1)), 1)  # still below: no duplicate

    def test_st_10_6_default_threshold_without_saved_setting(self):
        self.assertFalse(AttendanceThreshold.objects.exists())
        self.history(self.s1, self.a101, 74, 98)
        self.mark(self.a101, S001=A)  # 74/99
        self.assertEqual(len(self.notes(self.s1)), 1)

    def test_it_10_5_email_failure_still_delivers_in_app_and_is_logged(self):
        self.history(self.s1, self.a101, 75, 100)
        with mock.patch("apps.notifications.services.send_mail", side_effect=SMTPException("down")):
            self.mark(self.a101, S001=A)  # 75/101
        self.assertEqual(len(self.notes(self.s1)), 1)
        self.assertTrue(AttendanceSession.objects.filter(date=timezone.localdate()).exists())
        failure = AuditEntry.objects.get(action="notification.email_failed")
        self.assertIn("SMTPException", failure.new_value["error"])

    def test_missing_email_address_is_logged(self):
        self.s1.user.email = ""
        self.s1.user.save(update_fields=["email"])
        self.history(self.s1, self.a101, 75, 100)
        self.mark(self.a101, S001=A)
        self.assertEqual(len(self.notes(self.s1)), 1)
        self.assertTrue(AuditEntry.objects.filter(action="notification.email_failed").exists())

    def test_deactivated_student_is_not_notified(self):
        self.history(self.s1, self.a101, 75, 100)
        self.s1.user.is_active = False
        self.s1.user.save(update_fields=["is_active"])
        with self.captureOnCommitCallbacks(execute=True):
            evaluate_students()
        self.assertEqual(self.notes(self.s1), [])

    def test_failed_submission_creates_no_flag_or_notification(self):
        self.history(self.s1, self.a101, 75, 100)
        with self.assertRaises(PermissionDenied), self.captureOnCommitCallbacks(execute=True):
            submit_attendance(
                actor=self.f2.user,  # not this class's faculty
                assignment=self.a101,
                day=timezone.localdate(),
                period=1,
                statuses={self.s1.pk: A, self.s2.pk: P},
            )
        self.assertFalse(Notification.objects.exists())
        self.assertEqual(len(mail.outbox), 0)


class NotificationPageTests(Fixture):
    def test_student_sees_only_own_notifications_and_they_become_read(self):
        Notification.objects.create(recipient=self.s1.user, title="Low attendance: S1", body="mine")
        Notification.objects.create(recipient=self.s2.user, title="Low attendance: S2", body="theirs")
        self.client.force_login(self.s1.user)
        dashboard = self.client.get(reverse("dashboard_student"))
        self.assertContains(dashboard, "Notifications")
        self.assertEqual(dashboard.context["unread_notification_count"], 1)
        page = self.client.get(reverse("notification_list"))
        self.assertContains(page, "Low attendance: S1")
        self.assertNotContains(page, "Low attendance: S2")
        self.assertContains(page, "New")
        self.assertIsNotNone(Notification.objects.get(recipient=self.s1.user).read_at)
        self.assertIsNone(Notification.objects.get(recipient=self.s2.user).read_at)

    def test_staff_cannot_open_the_student_inbox(self):
        for user in (self.admin, self.f1.user):
            self.client.force_login(user)
            self.assertEqual(self.client.get(reverse("notification_list")).status_code, 403)


class ShortageListTests(Fixture):
    def test_admin_sees_all_subjects_and_overall(self):
        self.history(self.s1, self.a101, 74, 100)
        self.history(self.s2, self.a102, 1, 4)
        self.client.force_login(self.admin)
        page = self.client.get(reverse("shortage_list"))
        self.assertEqual(page.status_code, 200)
        self.assertContains(page, "74/100 (74.00%)")
        self.assertContains(page, "1/4 (25.00%)")
        self.assertContains(page, "Overall attendance")
        self.assertContains(page, "B.Tech CSE Year 2 A")
        overall, rows = page.context["overall_rows"], page.context["subject_rows"]
        self.assertEqual([r.student for r in overall], [self.s1, self.s2])
        expected = [(self.cs101, self.s1), (self.cs102, self.s2)]
        self.assertEqual([(r.subject, r.student) for r in rows], expected)

    def test_faculty_see_only_their_subjects(self):
        self.history(self.s1, self.a101, 74, 100)
        self.history(self.s2, self.a102, 1, 4)
        self.client.force_login(self.f1.user)
        page = self.client.get(reverse("shortage_list"))
        self.assertContains(page, "S001")
        self.assertNotContains(page, "S002")
        self.assertNotContains(page, "CS102")
        self.assertEqual(page.context["overall_rows"], [])

    def test_empty_list_message_and_equal_is_not_listed(self):
        self.history(self.s1, self.a101, 75, 100)
        self.client.force_login(self.f1.user)
        page = self.client.get(reverse("shortage_list"))
        self.assertContains(page, "No students are currently below the 75% threshold in your subjects.")

    def test_list_follows_corrections_and_threshold(self):
        self.history(self.s1, self.a101, 74, 100)
        self.client.force_login(self.f1.user)
        self.assertEqual(len(self.client.get(reverse("shortage_list")).context["subject_rows"]), 1)
        record = AttendanceRecord.objects.filter(student=self.s1, status=A).first()
        record.status = P
        record.save(update_fields=["status"])  # 75/100
        self.assertEqual(self.client.get(reverse("shortage_list")).context["subject_rows"], [])
        AttendanceThreshold.objects.create(pk=1, value=76)
        self.assertEqual(len(self.client.get(reverse("shortage_list")).context["subject_rows"]), 1)

    def test_deactivated_students_are_left_out(self):
        self.history(self.s1, self.a101, 74, 100)
        self.s1.user.is_active = False
        self.s1.user.save(update_fields=["is_active"])
        self.assertEqual(shortage_list_for(self.admin), ([], []))

    def test_students_are_denied(self):
        self.client.force_login(self.s1.user)
        self.assertEqual(self.client.get(reverse("shortage_list")).status_code, 403)

    def test_dashboard_links(self):
        self.client.force_login(self.admin)
        self.assertContains(self.client.get(reverse("dashboard_admin")), reverse("shortage_list"))
        self.client.force_login(self.f1.user)
        self.assertContains(self.client.get(reverse("dashboard_faculty")), reverse("shortage_list"))


class WeeklyEmailTests(Fixture):
    def test_st_10_5_each_faculty_gets_only_own_students_and_none_when_empty(self):
        self.history(self.s1, self.a101, 74, 100)
        self.history(self.s2, self.a102, 90, 100)
        result = send_weekly_faculty_emails(now=MONDAY)
        self.assertEqual(result, {"sent": 1, "empty": 2, "already_sent": 0, "failed": 0})
        self.assertEqual(len(mail.outbox), 1)
        email = mail.outbox[0]
        self.assertEqual(email.to, ["f001@example.edu"])
        self.assertIn("S001 Student S001 (B.Tech CSE Year 2 A): 74/100 (74.00%)", email.body)
        self.assertIn("CS101 – Programming", email.body)
        self.assertNotIn("S002", email.body)
        self.assertIn("02 Nov 2026", email.body)
        # The in-app list matches the email.
        _, rows = shortage_list_for(self.f1.user)
        self.assertEqual([r.student for r in rows], [self.s1])

    def test_rerun_in_same_week_does_not_duplicate_but_next_week_sends(self):
        self.history(self.s1, self.a101, 74, 100)
        send_weekly_faculty_emails(now=MONDAY)
        again = send_weekly_faculty_emails(now=MONDAY + datetime.timedelta(hours=3))
        self.assertEqual(again["already_sent"], 1)
        self.assertEqual(len(mail.outbox), 1)
        send_weekly_faculty_emails(now=MONDAY + datetime.timedelta(days=7))
        self.assertEqual(len(mail.outbox), 2)

    def test_failed_send_is_logged_and_retried_next_run(self):
        self.history(self.s1, self.a101, 74, 100)
        with mock.patch("apps.notifications.services.send_mail", side_effect=SMTPException("down")):
            result = send_weekly_faculty_emails(now=MONDAY)
        self.assertEqual(result["failed"], 1)
        self.assertFalse(WeeklyShortageEmail.objects.exists())
        self.assertTrue(AuditEntry.objects.filter(action="notification.weekly_email_failed").exists())
        self.assertEqual(send_weekly_faculty_emails(now=MONDAY)["sent"], 1)

    def test_management_command(self):
        self.history(self.s1, self.a101, 74, 100)
        out = StringIO()
        call_command("send_weekly_shortage_emails", stdout=out)
        self.assertIn("Sent 1", out.getvalue())
        self.assertEqual(len(mail.outbox), 1)
