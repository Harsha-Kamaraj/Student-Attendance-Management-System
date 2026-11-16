"""Below-threshold status, today's classes, and the student pages (no attendance advice)."""

from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from django.test import SimpleTestCase, TestCase
from django.urls import reverse

from apps.academics.models import Enrollment, Section, Subject, TeachingAssignment, TimetableSlot
from apps.academics.tests import make_faculty, make_student
from apps.notifications.models import Notification
from apps.notifications.services import _student_message

from .calculations import AttendanceOutlook, AttendanceTotals
from .models import AttendanceRecord, AttendanceSession, AttendanceThreshold, Status
from .schedule import today_overview

IST = ZoneInfo("Asia/Kolkata")


# Students see attended/held and, only when it applies, "Below the threshold". No advice on how many
# classes to attend or miss appears anywhere on their pages or in their alerts.
ADVICE = (
    "What you need",
    "Classes to attend",
    "classes left",
    "Attend ",
    "You can miss",
    "get back to",
    "already secured",
    "At or above",
    "at or above",
)


class OutlookTests(SimpleTestCase):
    def test_below_is_strictly_under_the_threshold(self):
        self.assertTrue(AttendanceOutlook(2, 3, 75).below)  # 66.67%
        self.assertFalse(AttendanceOutlook(3, 4, 75).below)  # exactly 75%
        self.assertFalse(AttendanceOutlook(4, 5, 75).below)  # 80%
        self.assertFalse(AttendanceOutlook(0, 0, 75).below)  # no classes yet
        self.assertEqual(AttendanceOutlook(4, 5, 75).display, "4/5 (80.00%)")

    def test_low_attendance_alert_lists_totals_without_advice(self):
        subject = Subject(code="CS101", name="Programming")
        message = _student_message([(subject, AttendanceTotals(1, 3)), (None, AttendanceTotals(5, 9))], 75)
        self.assertEqual(
            message,
            "Your attendance is below the required 75% in:\n"
            "- CS101 – Programming: 1/3 (33.33%)\n"
            "- Overall attendance: 5/9 (55.56%)\n"
            "\n"
            "If a mark looks wrong, contact your faculty member or the Admin.",
        )


class Fixture(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.faculty = make_faculty("F001")
        cls.student = make_student("S001")
        cls.section = Section.objects.create(class_name="B.Tech CSE Year 2", name="A")
        cls.subject = Subject.objects.create(code="CS101", name="Programming")
        cls.assignment = TeachingAssignment.objects.create(
            section=cls.section, subject=cls.subject, faculty=cls.faculty, planned_sessions=40
        )
        Enrollment.objects.create(student=cls.student, assignment=cls.assignment)
        AttendanceThreshold.objects.create(pk=1, value=75)
        for day, status in ((1, Status.PRESENT), (2, Status.ABSENT), (3, Status.ABSENT)):
            session = AttendanceSession.objects.create(
                assignment=cls.assignment, date=date(2026, 10, day), period=1, recorded_by=cls.faculty.user
            )
            AttendanceRecord.objects.create(session=session, student=cls.student, status=status)


class TodayOverviewTests(Fixture):
    def test_states_and_next_class_follow_the_clock_and_saved_sessions(self):
        monday = datetime(2026, 11, 9, 9, 30, tzinfo=IST)  # during period 2
        for period in (1, 2, 3):
            TimetableSlot.objects.create(assignment=self.assignment, weekday=0, period=period)
        AttendanceSession.objects.create(assignment=self.assignment, date=monday.date(), period=1)
        overview = today_overview(TeachingAssignment.objects.all(), now=monday)
        self.assertEqual([state for _, state in overview["today_rows"]], ["marked", "now", "upcoming"])
        self.assertEqual(overview["next_class"].period, 2)
        self.assertTrue(overview["next_class_now"])
        later = today_overview(TeachingAssignment.objects.all(), now=monday + timedelta(hours=3))
        self.assertEqual([state for _, state in later["today_rows"]], ["marked", "due", "due"])
        self.assertIsNone(later["next_class"])
        self.assertEqual(later["unmarked_count"], 2)

    def test_dashboard_count_matches_the_list_when_the_student_is_deactivated(self):
        # S001 is at 1/3, below 75%. Once deactivated, neither the dashboard nor the list counts them.
        self.student.user.is_active = False
        self.student.user.save(update_fields=["is_active"])
        self.client.force_login(self.faculty.user)
        dashboard = self.client.get(reverse("dashboard_faculty"))
        self.assertEqual(dashboard.context["students_below_overall"], 0)
        self.assertEqual(dashboard.context["subject_shortages"], 0)
        self.assertNotContains(dashboard, "Students below threshold in your assigned classes")
        self.assertContains(self.client.get(reverse("shortage_list")), "No students are currently below")

    def test_faculty_dashboard_shows_todays_classes_and_hides_empty_shortage_box(self):
        self.client.force_login(self.faculty.user)
        page = self.client.get(reverse("dashboard_faculty"))
        self.assertContains(page, "Today's classes")
        # S001 is at 1/3, so the shortage box is shown.
        self.assertContains(page, "Students below threshold in your assigned classes: 1")


class StudentPagesTests(Fixture):
    def setUp(self):
        self.client.force_login(self.student.user)

    def assert_no_advice(self, page):
        for words in ADVICE:
            self.assertNotContains(page, words)

    def bring_above_threshold(self):
        # S001 goes from 1/3 to 3/3.
        AttendanceRecord.objects.filter(student=self.student).update(status=Status.PRESENT)

    def test_dashboard_lists_each_subject_without_the_threshold_card(self):
        page = self.client.get(reverse("dashboard_student"))
        self.assertContains(page, "My subjects")
        self.assertContains(page, f"?subject={self.subject.pk}")
        self.assertContains(page, "1/3 (33.33%)")
        self.assertContains(page, "Your overall attendance is below the threshold.")
        self.assertNotContains(page, "My pages")
        self.assert_no_advice(page)

    def test_choosing_a_subject_lists_each_class_with_its_status(self):
        page = self.client.get(reverse("attendance_summary"), {"subject": self.subject.pk})
        self.assertContains(page, "Class-by-class: CS101 – Programming")
        self.assertContains(page, "Thu, 01 Oct 2026")
        self.assertContains(page, "Period 1 (8:00–9:00 am)")
        self.assertContains(page, "1/3 (33.33%) ▲ Below 75%")
        self.assertContains(page, "Below the 75% threshold")
        self.assert_no_advice(page)

    def test_notifications_page_lists_only_what_is_below_the_threshold(self):
        Notification.objects.create(recipient=self.student.user, title="Low attendance: below 75%", body="x")
        page = self.client.get(reverse("notification_list"))
        self.assertContains(page, "Below the 75% threshold")
        self.assertContains(page, "1/3 (33.33%)")
        self.assert_no_advice(page)
        self.assertNotContains(page, ">Back to dashboard</a>\n</div>")

    def test_a_student_at_or_above_the_threshold_sees_only_the_totals(self):
        self.bring_above_threshold()
        for url in ("dashboard_student", "attendance_summary", "notification_list"):
            page = self.client.get(reverse(url))
            self.assertNotContains(page, "Below the")
            self.assertNotContains(page, "is below the threshold")
            self.assert_no_advice(page)
        self.assertContains(self.client.get(reverse("attendance_summary")), "3/3 (100.00%)")
