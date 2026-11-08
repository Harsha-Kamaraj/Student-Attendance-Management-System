# BL-32 Demonstration and Handover

Backlog item BL-32 (issue #32), NFR-09. Prepared 8 November 2026.

This guide is for anyone who needs to run, demonstrate or assess the Student Attendance Management System: evaluators, new team members and the Admin who takes it over. It covers how to prepare a clean demo, a tested demonstration script, how each role uses the system, which requirements are complete, where the test evidence is, and what is still limited.

The demonstration script in section 3 was run on 8 November 2026 against a freshly migrated database loaded with the demo data. Every step worked except the alert email, which needs a real email address on the student account (see section 3, step 3).

## 1. Prepare a clean demo environment

Follow the full [Setup](../README.md#setup) section of the README the first time. In short:

1. Install Python 3.12+, PostgreSQL 16+ and Git, then clone the repository and install the dependencies into a virtual environment:

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate            # Windows: .venv\Scripts\activate
   pip install -r requirements-dev.txt
   ```

2. Create a **new, empty** PostgreSQL database for the demo. The demo data refuses to load into a database that already has it.
3. Copy `.env.example` to `.env` and set:
   - `SECRET_KEY`: generate one with the command shown in `.env.example`.
   - `DATABASE_URL`: points at the demo database.
   - `DEBUG=True`: the demo data only loads in development mode.
   - `BACKUP_ENCRYPTION_KEY`: generate one with the command shown in `.env.example`. Without it, backups are switched off.
4. Create the tables, load the demo data and start the server:

   ```bash
   python manage.py migrate
   python manage.py seed_test_data
   python manage.py runserver
   ```

5. Open http://127.0.0.1:8000/login/.

**Two-factor login.** It is on by default, so each account sets up an authenticator app (Google Authenticator or Microsoft Authenticator) at first login and saves its 10 backup codes. For a quicker walkthrough on your own machine only, add `OTP_REQUIRED=False` to `.env` and restart the server. Show two-factor login at least once with it switched on (step 6 of the script).

**Email.** By default, emails are printed in the terminal running the server; none are delivered. To send real email through Gmail, run `python scripts/configure_gmail.py` (Windows: `scripts\Configure-Gmail.cmd`) and restart the server. The demo accounts have **no email addresses**, so give any account you want to receive email a real address first, using **Manage students → Edit student** (or **Manage faculty → Edit faculty**).

## 2. Demo accounts

All demo accounts use the password **`Attend#2026`**. The data is fictional; see [Test_Data_Fixture.md](Test_Data_Fixture.md) for every figure.

| Role | Username | What it shows |
|---|---|---|
| Admin | `ADMIN1` | Everything |
| Faculty | `F001` | Teaches CS101 Programming in Section A (S001, S002, S004) |
| Faculty | `F002` | Teaches MA101 Mathematics in Section B (S001, S003) |
| Faculty | `F003` | Has no classes, so the dashboard shows zeros |
| Student | `S001` | Below 75% in both subjects and overall: 76/103 (73.79%) |
| Student | `S002` | Exactly 75.00%, so not flagged (equal is not below) |
| Student | `S003` | No classes held yet: "N/A – no classes yet" |
| Student | `S004` | 76.00%, above the threshold |

## 3. Demonstration script (about 15 minutes)

Use a normal and a private browser window so two people can be signed in at once.

| Step | Who | Do this | You should see |
|---|---|---|---|
| 1. Mark attendance | `F001` | **Mark attendance** → choose CS101, today's date and period 1 → **Load roster**. Mark S001 Absent, then click **Mark remaining as Present** → **Save complete attendance**. | The saved roster with S001 Absent and S002, S004 Present, marked "already saved". A second submission with different marks is refused. Future dates are greyed out. |
| 2. Correct a mark | `F001` | **Attendance history and corrections** → find today's S001 record → **Correct** → Present, reason "Arrived late" → **Save correction** → **View changes**. | The record is Present. The history shows old/new status, who changed it, when, and the reason. |
| 3. Low-attendance alert | `S001` | **Notifications**. | Alerts for CS101, MA101 and overall, created when step 1 saved the absence (the demo data starts with no alerts; saving a mark is what triggers the check). The email copy is printed in the server terminal, or delivered if Gmail is set up **and** S001 has a real email address. |
| 4. Student totals | `S001` | **View and filter my attendance**. Filter MA101 from 2 to 3 October 2026. | After steps 1–2: CS101 75/101 (74.26%), MA101 2/3 (66.67%), overall 77/104 (74.04%), highlighted as below 75%. The filter shows 1/2 (50.00%). |
| 5. Reports | `F001` | **Attendance reports** → today to today, CS101 → **Generate report** → download CSV and PDF. | A three-student report and two downloaded files. Faculty only see their own classes. |
| 6. Two-factor login | any | Log out and log in again with `OTP_REQUIRED=True`. | A QR code at first login, then 10 backup codes; later logins ask for the 6-digit code. |
| 7. Shortages and threshold | `ADMIN1` | **Students below threshold**, then **Configure attendance threshold** → 80 → **Save threshold**, and open the list again. | At 75%: S001 overall and in both subjects. At 80%: S001, S002 and S004 overall. |
| 8. Backup | `ADMIN1` | **Backup and recovery** → **Back up now** → **Download encrypted file**. | A completed, encrypted backup in the list and a `.sambak` download. |
| 9. Recovery | `ADMIN1` | Change the threshold to 85. Then **Restore…** on the backup from step 8, enter your password, tick the confirmation → **Restore backup**. Log in again. | The threshold is back to 80. Everyone is signed out and a safety backup was taken first. |
| 10. Permissions | `F001`, `S001` | Try to open `/students/create/` or `/backups/` as Faculty or Student. | Access is refused; nothing changes. |

Optional extras: **Forgot password?** on the login page (the Admin then sees "Reset requested" in **Accounts**), adding a student or faculty member, and the 15-minute idle sign-out.

A recorded walkthrough of the Sprint 2 product is in [demo/sprint-2](../demo/sprint-2/README.md); Sprint 1's is in [demo/sprint-1](../demo/sprint-1/README.md).

## 4. User guide by role

### Everyone

- **Log in** with your username (roll number, faculty ID or Admin username, any letter case) and password, then the 6-digit code from your authenticator app. No phone? Use **Email me a code** or one of your backup codes.
- **First login:** set up the authenticator app from the QR code, save the 10 backup codes (**Download as text file** or **Print**), then change your temporary password.
- **Forgot your password?** Use **Forgot password?** on the login page. The Admin is told, resets it, and a new temporary password is emailed to you.
- After 5 wrong passwords or 5 wrong codes, the account pauses for 15 minutes.
- **My profile** shows your own details, read-only. **Change password** is on the same page.
- **Log out** from the navigation bar. You are signed out automatically after 15 minutes without activity.

### Admin

| Task | Where |
|---|---|
| Add, edit, deactivate, reactivate or permanently delete students (a reason is required to delete) | **Manage students** |
| The same for faculty; faculty still teaching a class must be reassigned first | **Manage faculty** |
| Create sections ("Dept and sem", "Section", optional year), add subjects with their teacher, enroll students | **Manage classes, sections and enrollment** |
| Create, rename, offer or delete subjects (a subject with attendance cannot be deleted) | **Manage subjects** |
| Reset a password, resend login details, reset someone's two-factor login, handle reset requests | **Accounts and password resets** |
| Add another Admin | **Create Admin account** |
| Correct any record at any time, with a reason | **Attendance history and corrections** |
| Record a session faculty missed, with a reason | **Record missed attendance (reason required)** |
| Reports with CSV/PDF export for any student, class or subject | **Attendance reports** |
| See who is below the threshold, overall and per subject | **Students below threshold** |
| Change the threshold (default 75%) or the faculty correction window (default 2 days, 0–30) | **Configure attendance threshold**, **Configure faculty correction window** |
| Back up, schedule daily backups, download, import or restore | **Backup and recovery** |

### Faculty

| Task | Where |
|---|---|
| Mark attendance for an assigned class: every student must be marked; **Mark remaining as Present** fills the rest | **Mark attendance** |
| See your classes, students and subjects | **My classes**, **View students in my classes**, **My subjects** |
| Correct a mark within the correction window (until 23:59 IST two days after the session, by default); older changes go to the Admin | **Attendance history and corrections** → **Correct** |
| Reports and CSV/PDF exports for your own classes | **Attendance reports** |
| Students below the threshold in your subjects; you also get a Monday 08:00 email when the list is not empty | **Students below threshold in my subjects** |

### Student

| Task | Where |
|---|---|
| Attendance per subject and overall, with subject and date filters | **View and filter my attendance** |
| Alerts when a subject or overall figure falls below the threshold (one alert per drop, also by email) | **Notifications** |
| Your roll number, section, subjects and teachers | **My profile** |

## 5. Requirement completion

All 37 other backlog items are Done on the project board. BL-32 is this handover.

| Requirement | Delivered by | Status | Evidence (Test Case Document group) |
|---|---|---|---|
| FR-01 Account provisioning and login | BL-04, BL-34 | Complete | UC-01 |
| FR-02 Role management | BL-05 | Complete | UC-01 |
| FR-03 Student management | BL-07 | Complete | UC-02 |
| FR-04 Faculty management | BL-08, BL-11 | Complete | UC-03 |
| FR-05 Subject management | BL-09 | Complete | UC-04 |
| FR-06 Class/section management | BL-10, BL-11 | Complete | UC-05 |
| FR-07 Mark attendance | BL-12, BL-13 | Complete | UC-06 |
| FR-08 Update attendance | BL-17 | Complete | UC-07 |
| FR-09 View attendance | BL-15 | Complete | UC-08 |
| FR-10 Attendance history | BL-16 | Complete | UC-08 |
| FR-11 Attendance calculation | BL-14 | Complete | UC-06, UC-08 |
| FR-12 Attendance reports | BL-20 | Complete | UC-09 |
| FR-13 Low-attendance detection | BL-22, BL-24 | Complete | UC-10 |
| FR-14 Notifications | BL-23 | Complete | UC-10 |
| FR-15 Search and filter | BL-19 | Complete | UC-11 |
| FR-16 Report export | BL-21 | Complete | UC-09 |
| FR-17 Dashboards (and My profile) | BL-25 | Complete | UC-12 |
| FR-18 Modification history | BL-18 | Complete | UC-07 |
| FR-19 Backup and recovery | BL-26, BL-27 | Complete | UC-13 |
| FR-20 Logout | BL-06 | Complete | UC-12 |
| FR-21 Two-factor login | BL-33 | Complete | UC-01 |

| Requirement | Status | Basis |
|---|---|---|
| NFR-01 Performance | Met locally | PT_01–PT_03 passed with 50 users on one machine; repeat on the real server |
| NFR-02 to NFR-04 Security, authentication, authorization | Met | BL-05, BL-31; UC-01 and integration tests |
| NFR-05 Reliability, NFR-10 Data integrity | Met | BL-13 duplicate/partial-save protection; atomic corrections and restore |
| NFR-06 Availability | Not measured | Needs a month of monitoring on a deployed server (VAL-02) |
| NFR-07 Usability | Met | BL-30 manual workflow review and automated checks |
| NFR-08 Scalability | Met locally | PT_04: 1,000 students, 750,000 marks, 50 users |
| NFR-09 Maintainability | Met | Ruff lint/format, 530 automated tests, 94.89% line and 90.64% branch coverage |
| NFR-11 Privacy, NFR-14 Auditability | Met | Role-scoped data, owner-only credential email, audit log |
| NFR-12 Compatibility | Partly verified | Chrome, Chromium, Firefox and WebKit at 1440 px and 360 px; Edge, Safari and real phones not tested (VAL-03) |
| NFR-13 Backup and recovery | Met on macOS | Windows-only file-permission checks not run (VAL-04) |
| NFR-15 Accuracy | Met | All calculation tests pass |

## 6. Where the evidence is

| What | Where |
|---|---|
| Requirements, use cases, test plan, security requirements | [Documents/](.) (SRS, Use_Case_Flow, Test_Plan_Document, Security_Requirements_Specification) |
| Agreed rules and decisions (D-01 to D-23) | [BL-01_Decision_Log.md](BL-01_Decision_Log.md) |
| Part 3 test reports and the 207-case Test Case Document | [docs/](../docs/README.md) |
| Performance, browser and recovery verification records | [Documents/Verification/](Verification/) |
| Implementation notes per backlog item | `Documents/BL-*_Implementation.md` and related notes |
| Sprint demo videos | [demo/](../demo/) |
| Running the tests | `python manage.py test`, `ruff check .` (README, "Running tests and checks") |

## 7. Known limitations and non-blocking issues

None of these blocks the demonstration.

1. **Availability (NFR-06) is not measured.** It needs a month of monitoring on a real server during 08:00–18:00, Monday–Saturday.
2. **Browser and device coverage is partial.** Edge, Safari, the full "latest two versions" matrix and real Android/iOS phones were not tested; 360 px was emulated.
3. **Windows backup checks were not run.** Three file-permission tests only run on Windows. They account for most of the code not yet covered by tests.
4. **Performance was measured on one machine.** Repeat PT_01–PT_04 on the real server; network, HTTPS and email delays were not included.
5. **Email needs local setup.** Each machine needs its own Gmail app password in `.env`. The demo accounts have no email addresses, so alert emails, login-detail emails and emailed login codes only reach someone after a real address is added.
6. **Scheduled jobs need the server's scheduler.** Daily backups (`run_scheduled_backups`, every minute) and the Monday faculty email (`send_weekly_shortage_emails`) only run if cron or Task Scheduler calls them. Setting the time in the app does not install a scheduler.
7. **Password reset goes through the Admin.** There are no self-service reset links (BL-01 D-23), and a temporary password stays valid until it is used or replaced.
8. **Only Present and Absent exist.** "Late" and partial credit were deferred (D-06).
9. **Faculty corrections have a deadline.** After the window (default 2 days), only the Admin can correct or add a session, with a reason.
10. **Restoring a backup signs everyone out** and cancels emailed codes and backup codes; the restore needs a maintenance window. Backups over 256 MiB are refused, and connection poolers in transaction mode are not supported.
11. **The demo data is small.** It is for functional demos; the 1,000-student capacity data is generated separately by the BL-29 verification tools.
12. **Housekeeping:** pull request #58 holds an older draft of the Part 3 reports and can be closed; `main` has the current ones.
