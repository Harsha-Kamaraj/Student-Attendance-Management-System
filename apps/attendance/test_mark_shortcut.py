"""The dashboard's Mark attendance button opens the right class with date and period filled in."""

from datetime import date, datetime
from zoneinfo import ZoneInfo

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.academics.models import Enrollment, Section, Subject, TeachingAssignment, TimetableSlot
from apps.academics.tests import make_faculty, make_student

from .models import AttendanceSession
from .schedule import today_overview

IST = ZoneInfo("Asia/Kolkata")
MONDAY = date(2026, 11, 9)


def at(hour, minute=0):
    return datetime(2026, 11, 9, hour, minute, tzinfo=IST)


class MarkShortcutTests(TestCase):
    def setUp(self):
        self.teacher = make_faculty("F001")
        section = Section.objects.create(class_name="CSE 5", name="K")
        self.se = TeachingAssignment.objects.create(
            section=section,
            subject=Subject.objects.create(code="SE", name="Software Eng"),
            faculty=self.teacher,
        )
        self.ml = TeachingAssignment.objects.create(
            section=section,
            subject=Subject.objects.create(code="ML", name="Machine Learning"),
            faculty=self.teacher,
        )
        TimetableSlot.objects.create(assignment=self.se, weekday=0, period=2)  # 9:00-10:00
        TimetableSlot.objects.create(assignment=self.ml, weekday=0, period=4)  # 11:30-12:30
        Enrollment.objects.create(student=make_student("S001"), assignment=self.se)

    def target(self, now):
        return today_overview(TeachingAssignment.objects.all(), now=now)["mark_target"]

    def test_before_classes_the_next_class_is_chosen(self):
        target = self.target(at(8, 30))
        self.assertEqual((target.assignment, target.period), (self.se, 2))
        self.assertEqual(target.mark_query, f"assignment={self.se.pk}&date=2026-11-09&period=2")

    def test_a_class_happening_now_is_chosen(self):
        self.assertEqual(self.target(at(11, 45)).assignment, self.ml)

    def test_an_unmarked_finished_class_comes_before_the_next_class(self):
        self.assertEqual(self.target(at(10, 45)).assignment, self.se)

    def test_marked_classes_are_skipped_and_none_when_all_done(self):
        AttendanceSession.objects.create(assignment=self.se, date=MONDAY, period=2)
        self.assertEqual(self.target(at(10, 45)).assignment, self.ml)
        AttendanceSession.objects.create(assignment=self.ml, date=MONDAY, period=4)
        self.assertIsNone(self.target(at(13, 0)))

    def test_dashboard_button_links_to_a_prefilled_roster(self):
        self.client.force_login(self.teacher.user)
        from unittest.mock import patch

        with patch("apps.attendance.schedule.timezone.localtime", return_value=at(8, 30)):
            page = self.client.get(reverse("dashboard_faculty"))
        link = f"{reverse('attendance_mark')}?assignment={self.se.pk}&amp;date=2026-11-09&amp;period=2"
        self.assertContains(page, link, count=1)
        today = timezone.localdate().isoformat()
        roster = self.client.get(
            f"{reverse('attendance_mark')}?assignment={self.se.pk}&date={today}&period=2"
        )
        self.assertContains(roster, "S001")
