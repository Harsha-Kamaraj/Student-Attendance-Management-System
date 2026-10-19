import datetime

from django.db import IntegrityError, transaction
from django.db.models import ProtectedError
from django.test import TestCase

from apps.academics.models import Enrollment, Section, Subject, TeachingAssignment
from apps.academics.tests import make_faculty, make_student

from .models import AttendanceRecord, AttendanceSession, Status

DAY = datetime.date(2026, 10, 6)


class AttendanceTests(TestCase):
    def setUp(self):
        section = Section.objects.create(class_name="B.Tech CSE Year 2", name="A")
        self.subject = Subject.objects.create(code="CS101", name="Programming")
        self.faculty = make_faculty("F001")
        self.assignment = TeachingAssignment.objects.create(
            section=section, subject=self.subject, faculty=self.faculty
        )
        self.s1 = make_student("21CS001")
        self.s2 = make_student("21CS002")
        for student in (self.s1, self.s2):
            Enrollment.objects.create(student=student, assignment=self.assignment)
        self.session = AttendanceSession.objects.create(
            assignment=self.assignment,
            date=DAY,
            period=1,
            recorded_by=self.faculty.user,
            recorded_by_code="F001",
        )

    def new_session(self, **kwargs):
        values = {"assignment": self.assignment, "date": DAY, "period": 2} | kwargs
        return AttendanceSession.objects.create(**values)

    def test_duplicate_session_key_is_rejected(self):
        # BL-01 D-08: section + subject + date + period is unique.
        with transaction.atomic(), self.assertRaises(IntegrityError):
            self.new_session(period=1)

    def test_same_subject_and_date_in_another_period_is_allowed(self):
        self.new_session(period=2)
        self.assertEqual(AttendanceSession.objects.filter(date=DAY).count(), 2)

    def test_period_must_be_between_1_and_6(self):
        self.new_session(period=6)
        for period in (0, 7):
            with self.subTest(period=period), transaction.atomic(), self.assertRaises(IntegrityError):
                self.new_session(period=period)

    def test_only_present_and_absent_are_allowed(self):
        # BL-01 D-06: "L" (Late) or any other value is rejected by the database.
        AttendanceRecord.objects.create(session=self.session, student=self.s1, status=Status.PRESENT)
        with transaction.atomic(), self.assertRaises(IntegrityError):
            AttendanceRecord.objects.create(session=self.session, student=self.s2, status="L")

    def test_one_record_per_student_per_session(self):
        AttendanceRecord.objects.create(session=self.session, student=self.s1, status=Status.PRESENT)
        with transaction.atomic(), self.assertRaises(IntegrityError):
            AttendanceRecord.objects.create(session=self.session, student=self.s1, status=Status.ABSENT)

    def test_deleting_a_student_removes_only_their_records(self):
        # BL-01 D-04: a student's permanent deletion removes their attendance.
        AttendanceRecord.objects.create(session=self.session, student=self.s1, status=Status.PRESENT)
        AttendanceRecord.objects.create(session=self.session, student=self.s2, status=Status.ABSENT)
        self.s1.user.delete()
        self.assertEqual(
            list(self.session.records.values_list("student__roll_number", flat=True)), ["21CS002"]
        )

    def test_subject_with_attendance_cannot_be_deleted(self):
        # BL-01 D-05.
        with self.assertRaises(ProtectedError):
            self.subject.delete()

    def test_session_keeps_faculty_id_when_recorder_account_is_deleted(self):
        # BL-01 D-04: attendance recorded by a deleted faculty member is kept.
        recorder = make_faculty("F009")
        session = self.new_session(recorded_by=recorder.user, recorded_by_code="F009")
        recorder.user.delete()
        session.refresh_from_db()
        self.assertIsNone(session.recorded_by)
        self.assertEqual(session.recorded_by_code, "F009")

    def test_record_relationships_survive_reload(self):
        AttendanceRecord.objects.create(session=self.session, student=self.s1, status=Status.ABSENT)
        record = AttendanceRecord.objects.select_related(
            "student", "session__assignment__section", "session__assignment__subject"
        ).get(student__roll_number="21CS001")
        self.assertEqual(record.get_status_display(), "Absent")
        self.assertEqual(record.session.date, DAY)
        self.assertEqual(record.session.period, 1)
        self.assertEqual(record.session.assignment.subject.code, "CS101")
        self.assertEqual(str(record.session.assignment.section), "B.Tech CSE Year 2 A")
