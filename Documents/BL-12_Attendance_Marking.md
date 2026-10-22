# BL-12 / UC-06: Attendance marking

- Faculty select **only their assigned teaching assignments**, a date and period 1–6.
- Server rejects future dates, unauthorized assignments, unmarked students, unknown student IDs, and statuses other than Present (`P`) or Absent (`A`).
- Faculty may record a missed session only within the 2-day correction window (until the 2nd calendar day after the session date, IST). Older sessions are rejected with a "contact the Admin" message; the Admin can record them with a reason (BL-01 D-09, AR-06, AR-08, UC-06 1c).
- Only active enrolled students appear in new attendance sheets. Historical recorded attendance survives deactivation.
- **Mark remaining as Present** runs only on an explicit button click. The server never assumes an absent status.
- Admin may record missed sessions only with a required reason; audit records mark the override.
- Submission uses a transaction and stores one AttendanceSession with AttendanceRecords for the entire roster.
- Session uniqueness is established by the migration in BL-03. BL-13 adds serialization and idempotent retries.

Run `python manage.py test apps.attendance.test_marking` against PostgreSQL and check the normal application CI pipeline.
