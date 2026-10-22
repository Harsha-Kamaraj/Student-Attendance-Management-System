# BL-13: Complete, duplicate-safe attendance submissions

- `submit_attendance` uses `transaction.atomic` for session, records and audit entry.
- `TeachingAssignment.objects.select_for_update()` serializes submissions for the same class and subject on PostgreSQL.
- The unique `(assignment, date, period)` and `(session, student)` constraints remain the final integrity backstop.
- The same statuses submitted again return the existing session, without a second audit entry or student record.
- A different submission for an existing session is rejected. Editing saved attendance belongs to BL-17.
- Failed database writes roll back the session and all records, never leaving partial attendance.
- Original rosters are preserved on identical retries even if a later enrollment was removed.

Verification: `python manage.py test apps.attendance.test_submission_safety`; test the concurrency case on PostgreSQL, not SQLite.
