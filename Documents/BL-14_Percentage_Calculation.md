# BL-14: Subject and overall attendance percentages

Implements issue #14 using BL-01 D-10 to D-13. Student dashboard → **View my attendance percentages** opens `/attendance/mine/`. The report uses the authenticated student's profile; query parameters cannot select another student. Faculty and Admin cannot open this student-only report.

- Subject percentage = attended / held × 100. Display counts and percentage, such as `10/12 (83.33%)`.
- Overall percentage pools all counts: `10/12 + 8/10 = 18/22 (81.82%)`. Subject percentages are never averaged.
- Use `Decimal` and `ROUND_HALF_UP` to two decimal places: `2/3 → 66.67%`, `1/160 → 0.63%`.
- Zero held classes show `N/A – no classes yet`, with no below-threshold flag.
- Threshold comparison uses exact integer counts, independent of display rounding.
- Count persisted records belonging to the student. Sessions without a student record do not become absences.
- Include current enrollments with no recorded classes and historical subject records after enrollment removal or deactivation.
- Query counts on each request, storing no percentage cache. New attendance and subsequent valid corrections update both subject and overall totals immediately.

`student_attendance_summary(student, assignments=None)` returns typed subject rows and pooled totals. An optional assignment scope is available for future faculty reports. Two queries serve any number of subjects.

Verification: `python manage.py test apps.attendance.test_calculations apps.attendance.test_summary`. The tests cover known pooled results, half-up rounding, zero classes, all present/absent, missing records, student and assignment isolation, historical enrollment, corrected records, bounded query count, and report authorization. Correction editing itself belongs to its own backlog item.
