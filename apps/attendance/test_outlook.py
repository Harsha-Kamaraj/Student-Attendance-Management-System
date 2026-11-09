"""How many classes a student needs, the semester plan, today's classes, and the student pages."""

from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from django.test import SimpleTestCase, TestCase
from django.urls import reverse

from apps.academics.models import Enrollment, Section, Subject, TeachingAssignment, TimetableSlot
from apps.academics.tests import make_faculty, make_student
from apps.notifications.models import Notification

from .calculations import AttendanceOutlook, classes_can_miss, classes_needed
from .models import AttendanceRecord, AttendanceSession, AttendanceThreshold, Status
from .schedule import today_overview

IST = ZoneInfo("Asia/Kolkata")


class ClassesNeededTests(SimpleTestCase):
    def test_classes_needed_reaches_the_threshold_exactly(self):
        # 76/102 at 85%: (76 + 72) / (102 + 72) = 148/174 = 85.06%, while 71 more gives 84.97%.
        self.assertEqual(classes_needed(76, 102, 85), 72)
        self.assertEqual(classes_needed(3, 4, 80), 1)  # 4/5 = 80%
        self.assertEqual(classes_needed(8, 10, 80), 0)  # exactly at the threshold
        self.assertEqual(classes_needed(0, 0, 75), 0)  # no classes yet
        self.assertIsNone(classes_needed(9, 10, 100))

    def test_classes_can_miss_keeps_the_student_at_or_above(self):
        self.assertEqual(classes_can_miss(10, 10, 75), 3)  # 10/13 = 76.9%; 10/14 = 71.4%
        self.assertEqual(classes_can_miss(3, 4, 75), 0)
        self.assertEqual(classes_can_miss(1, 4, 75), 0)

    def test_messages_without_a_semester_plan(self):
        self.assertEqual(AttendanceOutlook(0, 0, 75).message, "No classes held yet.")
        self.assertEqual(AttendanceOutlook(3, 5, 75).message, "Attend the next 3 classes to get back to 75%.")
        self.assertIn("You can miss 3 classes", AttendanceOutlook(10, 10, 75).message)
        self.assertIn("cannot be reached", AttendanceOutlook(9, 10, 100).message)
        self.assertEqual(
            AttendanceOutlook(3, 4, 75).message, "Attend your next class to stay at 75% or above."
        )

    def test_messages_with_a_semester_plan(self):
        # 40 planned at 75% needs 30 attended; 20 attended of 25 held leaves 15 classes, 10 needed.
        outlook = AttendanceOutlook(20, 25, 75, planned=40)
        self.assertEqual((outlook.remaining, outlook.must_attend), (15, 10))
        self.assertEqual(
            outlook.message,
            "Attend at least 10 of the 15 classes left this semester to finish at 75% or above.",
        )
        self.assertIn("already secured", AttendanceOutlook(30, 32, 75, planned=40).message)
        impossible = AttendanceOutlook(5, 25, 75, planned=40)
        self.assertIn("Even attending all 15 classes left", impossible.message)
        self.assertIn("50.00%", impossible.message)
        self.assertEqual(AttendanceOutlook(1, 2, 75).display, "1/2 (50.00%)")


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

    def test_dashboard_lists_each_subject_without_the_threshold_card(self):
        page = self.client.get(reverse("dashboard_student"))
        self.assertContains(page, "My subjects")
        self.assertContains(page, f"?subject={self.subject.pk}")
        self.assertContains(page, "1/3 (33.33%)")
        self.assertNotContains(page, "My pages")

    def test_choosing_a_subject_lists_each_class_with_its_status(self):
        page = self.client.get(reverse("attendance_summary"), {"subject": self.subject.pk})
        self.assertContains(page, "Class-by-class: CS101 – Programming")
        self.assertContains(page, "Thu, 01 Oct 2026")
        self.assertContains(page, "Period 1 (8:00–9:00 am)")
        # Semester plan: 40 classes at 75% needs 30, so 29 of the 37 remaining.
        self.assertContains(page, "Attend at least 29 of the 37 classes left this semester")

    def test_notifications_page_shows_where_the_student_stands(self):
        Notification.objects.create(recipient=self.student.user, title="Low attendance: below 75%", body="x")
        page = self.client.get(reverse("notification_list"))
        self.assertContains(page, "Where you stand now")
        self.assertContains(page, "Attend at least 29 of the 37 classes left this semester")
        self.assertNotContains(page, ">Back to dashboard</a>\n</div>")
