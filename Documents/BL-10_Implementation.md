# BL-10 — Classes, sections and enrollment (#10)

## Scope

- Admin creates and views class/section pairs using the existing `Section` model.
- Section names are validated for duplicates (including differences in letter case).
- Admin adds active students to subject-specific section rosters through `TeachingAssignment`.
  Server-side form queryset restriction prevents cross-section assignment tampering.
- A student cannot join two sections for the same subject; the error names their existing section.
  The existing `(student, subject)` database unique constraint protects concurrent changes.
- Admin may remove an enrollment. Historical attendance records are deliberately not deleted.
- The existing BL-05 `sections.manage` permission enforces server-side Admin-only changes.
- Existing inactive enrollments remain visible with an Inactive label for historical context,
  but inactive students cannot be newly enrolled through this workflow.

## Dependencies

Apply this implementation after BL-07. Subject creation and faculty teaching assignments
belong to BL-09 and BL-11, respectively. Until those screens are delivered, section rosters
can be tested with seeded subject and assignment records; they are not created by BL-10.

## Verification

`python manage.py test apps.academics.test_section_enrollment`

Then `python manage.py test`, `python manage.py makemigrations --check --dry-run`,
`ruff check .` and `ruff format --check .`.
