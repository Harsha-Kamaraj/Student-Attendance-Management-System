# BL-07 — Student management (#7)

## Scope

Admin-only creation, updates, deactivation/reactivation and permanent deletion of student profiles.
All roles may view only their permitted student profiles via the BL-05 `visible_students` scope.

- Creating a student provisions a STUDENT account with username equal to uppercase roll number and a
  one-time temporary password, using the existing account provisioning service.
- Class and section are validated together: the selected section must belong to the selected class.
  `Student.home_section` is a home-section link; course-specific participation remains in `Enrollment`.
  It is nullable for pre-existing records but required by new student management forms.
- Roll numbers are immutable after creation because they are account login identifiers.
- Deactivation sets `User.is_active=False`. It keeps enrollments, attendance and audit entries.
  New attendance workflows must exclude inactive accounts from new session sheets.
- Permanent deletion requires a reason and explicit confirmation. It deletes the account/profile,
  enrollments and the student's attendance records, while retaining append-only audit events
  (BL-01 D-04).

## Verification

`python manage.py test apps.academics.test_student_management`

Then `python manage.py test`, `python manage.py makemigrations --check --dry-run`,
`ruff check .` and `ruff format --check .`.

## Dependencies

Sections must exist for new student creation; the section management screens are delivered in BL-10.
