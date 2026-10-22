# Reusable Synthetic Test Data — BL-28

This fixture is fictional and must be used only in local development or an isolated test database. Do not substitute real student names, roll numbers, email addresses, or attendance records.

## Accounts

| Role | Username | Example email | Scope |
|---|---|---|---|
| Admin | `ADMIN1` | `admin1@example.test` | All records |
| Faculty | `F001` | `f001@example.test` | Teaches CS101 in Section A |
| Faculty | `F002` | `f002@example.test` | Teaches MA101 in Section B |
| Faculty | `F003` | `f003@example.test` | No assigned classes |
| Student | `S001` | `s001@example.test` | Enrolled in CS101 and MA101 |
| Student | `S002` | `s002@example.test` | Enrolled in CS101 and MA101 |
| Student | `S003` | `s003@example.test` | No attendance records |

Use a test-only password that satisfies the repository password validator, such as `Attend#2026`. Never use the real admin password in fixtures, source files, or commits.

## Academic data

| Record | Value |
|---|---|
| Class / section A | `B.Tech CSE Year 2`, `A` |
| Class / section B | `B.Tech CSE Year 2`, `B` |
| Subject 1 | `CS101`, Programming |
| Subject 2 | `MA101`, Mathematics |
| Assignment A | F001 teaches CS101 in Section A |
| Assignment B | F002 teaches MA101 in Section B |

## Attendance boundary fixtures (default threshold 75%)

| Student | Subject | Present / held | Expected shortage? |
|---|---|---:|---|
| S001 | CS101 | 74 / 100 | Yes |
| S002 | CS101 | 75 / 100 | No; equality is not below threshold |
| S003 | CS101 | 76 / 100 | No |
| S003 | MA101 | 0 / 0 | No; zero-record subjects are not flagged |

For a small deterministic unit-test fixture, use S001 = 2/3, S002 = 3/4, and a separate student with no records. Expected threshold behavior is identical to the large-count examples.

## Date-filter fixture (inclusive dates)

| Date (IST) | Subject | Status for S001 |
|---|---|---|
| 2026-10-01 | CS101 | Present |
| 2026-10-02 | CS101 | Absent |
| 2026-10-03 | MA101 | Present |

Expected results:
- Subject CS101 with range 2026-10-02 through 2026-10-02 shows `0/1 (0.00%)`.
- Range 2026-10-02 through 2026-10-03 includes both boundary dates.
- Reversed dates are rejected with a validation message.
- A date range with no records shows a clear empty state and `N/A – no classes yet`.

## Traceability

- **BL-15 / FR-09 / UC-08:** own-student access, subject/date filtering, inclusive boundaries, no-match state, percentage consistency.
- **BL-22 / FR-13 / UC-10:** threshold defaults to 75, accepts integers 1–100, rejects invalid values, exact below/equal/above boundary, zero-record behavior, Admin-only writes.
- **BL-25 / FR-17 / UC-12:** role routing, role-scoped dashboard statistics, shortage counts, updates after attendance changes, no-data behavior.
- **BL-28:** concrete steps, positive/negative/permission/boundary tests, reusable synthetic data, and non-functional performance tests.

## Non-functional test targets

Execute only in a controlled staging environment with synthetic data:
- At least 95% of common requests complete within 2 seconds.
- Complete attendance submission for 60 students completes within 3 seconds.
- One-semester section report generation completes within 10 seconds.
- Test 50 concurrent users, 1,000 students, and 60 faculty.
- Record environment, sample size, median, p95, error count, and any data-integrity failures in the test-plan results.
