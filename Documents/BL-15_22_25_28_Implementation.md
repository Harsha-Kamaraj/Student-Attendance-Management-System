# Assigned Backlog Implementation Notes — BL-15, BL-22, BL-25, BL-28

## BL-15 / Issue #15 — Student attendance report
- The report uses the authenticated student's `Student` profile; query parameters cannot select a different student.
- Optional subject, start-date, and end-date filters are validated server-side.
- Date bounds are inclusive. Reversed date ranges are rejected.
- Filtered totals are computed from persisted attendance records through `student_attendance_summary`; no percentages are stored or cached.
- A filtered query with no matching records shows an explicit empty state. The unfiltered no-class state remains `N/A — no classes yet`.
- Existing role restriction remains Student-only.

## BL-22 / Issue #22 — Attendance threshold
- The institutional default is 75 percent if the singleton setting row has not yet been saved.
- Admin can configure a whole-number threshold from 1 through 100 at `/attendance/threshold/`.
- The setting is persisted in `AttendanceThreshold` (singleton primary key 1), with a database check constraint.
- Faculty and Student requests are rejected by the existing `threshold.configure` permission.
- Shortage checks compare exact counts (`attended * 100 < threshold * held`); equality is not flagged and zero-record cases are ignored.
- Dashboard shortage metrics are computed live from persisted attendance records, so saved attendance corrections are reflected on the next request.

## BL-25 / Issue #25 — Role-specific dashboards
- Admin dashboard shows institution-wide student, faculty, section, and session counts plus current threshold and shortage counts.
- Faculty dashboard scopes classes, subjects, students, sessions, and shortage counts to the signed-in faculty member's assignments.
- Student dashboard shows only the signed-in student's own overall attendance and below-threshold status.
- Dashboards do not cache attendance calculations.

## BL-28 / Issue #28 — Test plan and reusable test data
- `Test_Plan_Document.docx` now has concrete cases for report filters, privacy, threshold boundaries, Admin-only configuration, dashboard scope/no-data, and performance/capacity targets.
- `Test_Data_Fixture.md` provides fictional accounts, academic records, threshold boundary examples, and traceability to BL/FR/UC identifiers.
- Execute all automated tests and the documented performance tests in an isolated environment before merging.
