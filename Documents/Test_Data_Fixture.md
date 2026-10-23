# Reusable Synthetic Test Data — BL-28

All names, roll numbers and emails are fictional. Use this data only in local development or an isolated test database; never substitute real student information.

## Loading it

```bash
python manage.py migrate
python manage.py seed_test_data
```

The command creates everything below in one step. It runs only when `DEBUG=True` and refuses to run if the accounts already exist, so it cannot overwrite real data. To reload, use a fresh database. Its figures are checked by `apps/academics/test_seed_data.py`, so this document and the data cannot drift apart.

Every account's password is **`Attend#2026`** (no forced password change).

## Accounts

| Role | Username | Scope |
|---|---|---|
| Admin | `ADMIN1` | All records |
| Faculty | `F001` | Teaches CS101 in Section A (students S001, S002, S004) |
| Faculty | `F002` | Teaches MA101 in Section B (students S001, S003) |
| Faculty | `F003` | No classes |
| Student | `S001` | CS101 (Section A) and MA101 (Section B) |
| Student | `S002` | CS101 (Section A) |
| Student | `S003` | MA101 (Section B); joined after its sessions, so **no attendance records** |
| Student | `S004` | CS101 (Section A) |

## Academic data

| Record | Value |
|---|---|
| Sections | `B.Tech CSE Year 2` A and B |
| Subjects | `CS101` Programming, `MA101` Mathematics |
| Teaching assignments | F001 → CS101 in A; F002 → MA101 in B |

## Attendance

- **CS101, Section A:** 100 sessions from 1 to 17 June 2026 (periods 1–6 each day), recorded by F001.
- **MA101, Section B:** 3 sessions for S001 on 1 Oct (Present), 2 Oct (Absent) and 3 Oct 2026 (Present), period 1, recorded by F002.

| Student | CS101 | MA101 | Overall | Below 75%? |
|---|---|---|---|---|
| S001 | 74/100 (74.00%) | 2/3 (66.67%) | 76/103 (73.79%) | **Yes** (both subjects and overall) |
| S002 | 75/100 (75.00%) | — | 75/100 (75.00%) | No — equal is not below |
| S004 | 76/100 (76.00%) | — | 76/100 (76.00%) | No |
| S003 | — | N/A – no classes yet | N/A – no classes yet | No — zero classes are never flagged |

## Dashboard figures (threshold 75%)

| Dashboard | Figures |
|---|---|
| Admin | 4 students, 3 faculty, 2 sections, 103 sessions; 1 student below overall; 2 subject shortages (S001 CS101, S001 MA101) |
| F001 | 1 class, 3 students, 100 sessions; 1 below; 1 shortage (S001 CS101) |
| F002 | 1 class, 2 students, 3 sessions; 1 below; 1 shortage (S001 MA101) |
| F003 | All zero |
| At threshold 80% (Admin) | 3 students below overall (S001, S002, S004); 4 subject shortages |

## Date-filter examples (S001, inclusive dates)

| Filter | Result |
|---|---|
| MA101, 2 Oct to 2 Oct 2026 | 0/1 (0.00%) |
| MA101, 2 Oct to 3 Oct 2026 | 1/2 (50.00%) — both boundary dates included |
| Any subject, 10 Oct to 11 Oct 2026 | No records — "No attendance records match these filters." |
| Start date after end date | Rejected — "End date must be on or after the start date." |

## Traceability

- **BL-15 / FR-09 / UC-08:** own-student access, subject and date filters, inclusive boundaries, no-match state.
- **BL-22 / FR-13 / UC-10:** default 75, whole numbers 1–100, below/equal/above boundaries (S001/S002/S004), zero-record student (S003), Admin-only changes.
- **BL-25 / FR-17 / UC-12:** role-scoped dashboard figures, including a faculty member with no classes (F003).
- **BL-28:** the test plan's concrete cases use these accounts and figures.

## Non-functional tests

Performance and capacity tests (test plan PT_01–PT_04) need a larger synthetic dataset — 1,000 students, 60 faculty and one semester of sessions — in a staging environment. This small dataset is for functional testing only.
