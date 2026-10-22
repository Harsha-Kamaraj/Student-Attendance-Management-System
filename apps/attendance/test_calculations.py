"""Calculation examples and persistence regressions for BL-14 / NFR-15."""

import datetime
from decimal import Decimal

from django.test import TestCase

from apps.academics.models import Enrollment, Section, Subject, TeachingAssignment
from apps.academics.tests import make_student

from .calculations import AttendanceTotals, student_attendance_summary
from .models import AttendanceRecord, AttendanceSession, Status


class AttendanceCalculationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.student = make_student("S001")
        cls.other_student = make_student("S002")
        section = Section.objects.create(class_name="CSE", name="A")
        cls.programming = Subject.objects.create(code="CS101", name="Programming")
        cls.maths = Subject.objects.create(code="MA101", name="Mathematics")
        cls.a_programming = TeachingAssignment.objects.create(section=section, subject=cls.programming)
        cls.a_maths = TeachingAssignment.objects.create(section=section, subject=cls.maths)
        for assignment in (cls.a_programming, cls.a_maths):
            Enrollment.objects.create(student=cls.student, assignment=assignment)

    def add_classes(self, assignment, *, attended, held, student=None):
        student = student or self.student
        first_day = datetime.date(2026, 1, 1)
        sessions = AttendanceSession.objects.bulk_create(
            AttendanceSession(
                assignment=assignment,
                date=first_day + datetime.timedelta(days=number // 6),
                period=number % 6 + 1,
            )
            for number in range(held)
        )
        return AttendanceRecord.objects.bulk_create(
            AttendanceRecord(
                student=student,
                session=session,
                status=Status.PRESENT if number < attended else Status.ABSENT,
            )
            for number, session in enumerate(sessions)
        )

    def test_known_subject_and_pooled_overall_results(self):
        self.add_classes(self.a_programming, attended=10, held=12)
        self.add_classes(self.a_maths, attended=8, held=10)
        summary = student_attendance_summary(self.student)
        self.assertEqual([row.subject for row in summary.subjects], [self.programming, self.maths])
        self.assertEqual([row.display for row in summary.subjects], ["10/12 (83.33%)", "8/10 (80.00%)"])
        self.assertEqual(summary.overall.attended, 18)
        self.assertEqual(summary.overall.held, 22)
        self.assertEqual(summary.overall.percentage, Decimal("81.82"))
        self.assertEqual(summary.overall.display, "18/22 (81.82%)")

    def test_rounding_is_half_up_with_two_decimal_places(self):
        self.add_classes(self.a_programming, attended=1, held=160)
        self.add_classes(self.a_maths, attended=2, held=3)
        summary = student_attendance_summary(self.student)
        self.assertEqual([row.percentage for row in summary.subjects], [Decimal("0.63"), Decimal("66.67")])
        self.assertEqual(summary.subjects[0].display, "1/160 (0.63%)")

    def test_enrolled_subjects_without_classes_and_overall_are_na(self):
        summary = student_attendance_summary(self.student)
        for totals in [*summary.subjects, summary.overall]:
            self.assertEqual(totals.attended, 0)
            self.assertEqual(totals.held, 0)
            self.assertIsNone(totals.percentage)
            self.assertEqual(totals.display, "N/A – no classes yet")
            self.assertFalse(totals.is_below_threshold())

    def test_student_without_enrollment_or_records_has_no_subjects(self):
        summary = student_attendance_summary(self.other_student)
        self.assertEqual(summary.subjects, [])
        self.assertIsNone(summary.overall.percentage)

    def test_all_present_and_all_absent_display_endpoints(self):
        self.add_classes(self.a_programming, attended=3, held=3)
        self.add_classes(self.a_maths, attended=0, held=2)
        summary = student_attendance_summary(self.student)
        self.assertEqual([row.display for row in summary.subjects], ["3/3 (100.00%)", "0/2 (0.00%)"])
        self.assertEqual(summary.overall.display, "3/5 (60.00%)")

    def test_new_attendance_and_saved_corrections_recalculate_immediately(self):
        self.assertIsNone(student_attendance_summary(self.student).overall.percentage)
        records = self.add_classes(self.a_programming, attended=1, held=2)
        self.assertEqual(student_attendance_summary(self.student).overall.display, "1/2 (50.00%)")
        records[1].status = Status.PRESENT
        records[1].save(update_fields=["status"])
        self.assertEqual(student_attendance_summary(self.student).overall.display, "2/2 (100.00%)")

    def test_missing_records_do_not_count_as_absences(self):
        self.add_classes(self.a_programming, attended=1, held=2, student=self.other_student)
        summary = student_attendance_summary(self.student)
        self.assertEqual(summary.subjects[0].held, 0)
        self.assertIsNone(summary.overall.percentage)

    def test_other_students_records_do_not_affect_totals(self):
        records = self.add_classes(self.a_programming, attended=1, held=2)
        AttendanceRecord.objects.bulk_create(
            AttendanceRecord(session=record.session, student=self.other_student, status=Status.PRESENT)
            for record in records
        )
        self.assertEqual(student_attendance_summary(self.student).overall.display, "1/2 (50.00%)")

    def test_historical_subjects_remain_after_enrollment_removal_and_deactivation(self):
        self.add_classes(self.a_programming, attended=2, held=3)
        self.student.enrollments.filter(assignment=self.a_programming).delete()
        self.student.user.is_active = False
        self.student.user.save(update_fields=["is_active"])
        summary = student_attendance_summary(self.student)
        self.assertEqual(summary.subjects[0].subject, self.programming)
        self.assertEqual(summary.overall.display, "2/3 (66.67%)")

    def test_scope_filters_both_history_and_zero_class_enrollments(self):
        self.add_classes(self.a_programming, attended=1, held=1)
        self.add_classes(self.a_maths, attended=0, held=2)
        assignments = TeachingAssignment.objects.filter(pk=self.a_programming.pk)
        summary = student_attendance_summary(self.student, assignments=assignments)
        self.assertEqual([row.subject for row in summary.subjects], [self.programming])
        self.assertEqual(summary.overall.display, "1/1 (100.00%)")
        summary = student_attendance_summary(self.student, assignments=TeachingAssignment.objects.none())
        self.assertEqual(summary.subjects, [])
        self.assertIsNone(summary.overall.percentage)

    def test_scope_includes_current_subject_without_records(self):
        self.add_classes(self.a_programming, attended=1, held=1)
        summary = student_attendance_summary(
            self.student, assignments=TeachingAssignment.objects.filter(pk=self.a_maths.pk)
        )
        self.assertEqual([row.subject for row in summary.subjects], [self.maths])
        self.assertEqual(summary.subjects[0].display, "N/A – no classes yet")

    def test_records_in_multiple_sections_for_a_subject_are_combined(self):
        self.add_classes(self.a_programming, attended=1, held=2)
        new_section = Section.objects.create(class_name="CSE", name="B")
        new_assignment = TeachingAssignment.objects.create(section=new_section, subject=self.programming)
        self.student.enrollments.filter(assignment=self.a_programming).delete()
        Enrollment.objects.create(student=self.student, assignment=new_assignment)
        self.add_classes(new_assignment, attended=2, held=2)
        summary = student_attendance_summary(self.student)
        self.assertEqual(summary.subjects[0].display, "3/4 (75.00%)")

    def test_query_count_is_bounded_independent_of_subject_count(self):
        self.add_classes(self.a_programming, attended=2, held=3)
        self.add_classes(self.a_maths, attended=1, held=2)
        with self.assertNumQueries(2):
            summary = student_attendance_summary(self.student)
            self.assertEqual([row.subject.code for row in summary.subjects], ["CS101", "MA101"])
            self.assertEqual(summary.overall.display, "3/5 (60.00%)")

    def test_threshold_uses_exact_counts_and_equality_is_not_flagged(self):
        # Both values display 75.00%, but only the first is exactly below 75%.
        self.assertTrue(AttendanceTotals(attended=14999, held=20000).is_below_threshold())
        self.assertFalse(AttendanceTotals(attended=3, held=4).is_below_threshold())
        self.assertFalse(AttendanceTotals(attended=0, held=0).is_below_threshold())
