# BL-32 Demonstration and Handover

Backlog item BL-32 (issue #32), NFR-09. Prepared 8 November 2026; updated 9 November 2026 for the redesigned interface, timetable, semester classes and emailed login details.

This guide is for anyone who needs to run, demonstrate or assess the Student Attendance Management System: evaluators, new team members and the Admin who takes it over. It covers how to prepare a clean demo, a tested demonstration script, how each role uses the system, which requirements are complete, where the test evidence is, and what is still limited.

The demonstration script in section 3 was rerun on 9 November 2026 against a freshly migrated database loaded with the demo data; all 15 checks passed. Alert emails only reach a student who has a real email address on their account (see section 3, step 4).

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

**Email.** By default, emails are printed in the terminal running the server; none are delivered. To send real email through Gmail, run `python scripts/configure_gmail.py` (Windows: `scripts\Configure-Gmail.cmd`) and restart the server. The demo accounts have **no email addresses**, so give any account you want to receive email a real address first, using **Students → View → Edit student** (or **Faculty → View → Edit**).

## 2. Demo accounts

All demo accounts use the password **`Attend#2026`**. The data is fictional; see [Test_Data_Fixture.md](Test_Data_Fixture.md) for every figure.

| Role | Username | What it shows |
|---|---|---|
| Admin | `ADMIN1` | Everything |
| Faculty | `F001` | Teaches CS101 Programming in Section A (S001, S002, S004); timetabled Monday period 2, Wednesday period 1, Friday period 3 |
| Faculty | `F002` | Teaches MA101 Mathematics in Section B (S001, S003); timetabled Monday period 4, Tuesday period 2, Thursday period 5 |
| Faculty | `F003` | Has no classes, so the dashboard shows zeros |
| Student | `S001` | Below 75% in both subjects and overall: 76/103 (73.79%). Semester classes: CS101 120, MA101 40 |
| Student | `S002` | Exactly 75.00%, so not flagged (equal is not below) |
| Student | `S003` | No classes held yet: "N/A – no classes yet" |
| Student | `S004` | 76.00%, above the threshold |

## 3. Demonstration script (about 15 minutes)

Use a normal and a private browser window so two people can be signed in at once. Every page has a sidebar on the left (on a phone, open it with the ☰ button); the steps name the sidebar entry to click.

| Step | Who | Do this | You should see |
|---|---|---|---|
| 1. Today's classes | `F001` | Log in and look at the dashboard. | A banner with today's date and the next class, and **Today's classes** from the timetable. On a Monday: CS101, Period 2 (9:00–10:00 am); after 10:00 it is flagged **not marked yet**. Saturday and Sunday have no classes. |
| 2. Mark attendance | `F001` | **Mark attendance** next to today's class (or sidebar **Mark attendance** → CS101, today, the timetabled period → **Load roster**). Mark S001 Absent, click **Mark remaining as Present** → **Save complete attendance**. | The saved roster with S001 Absent and S002, S004 Present, marked "already saved". A second submission with different marks is refused. Future dates are greyed out. The class shows **Marked** on the dashboard. |
| 3. Correct a mark | `F001` | Sidebar **History and corrections** → **Apply filters** → find today's S001 record → **Correct** → Present, reason "Arrived late" → **Save correction** → **View changes**. | The record is Present. The history shows old/new status, who changed it, when, and the reason. |
| 4. Low-attendance alert | `S001` | Sidebar **Notifications**. | **Where you stand now**: CS101 75/101 (74.26%), MA101 2/3 (66.67%) and overall 77/104 (74.04%), each with the classes needed, e.g. "Attend at least 15 of the 19 classes left this semester". Below it, the alert created when step 2 saved the absence ("attend the next 7 classes to get back to 75%"). The email copy is printed in the server terminal, or delivered if Gmail is set up **and** S001 has a real email address. |
| 5. Student view | `S001` | **Dashboard**, then click the **CS101** card. Back on **My attendance**, filter MA101 from 2 to 3 October 2026. | Overall attendance and **Subjects below threshold: 2**, then one card per subject with its percentage. The CS101 page lists every class with date, time and Present/Absent (20 per page). The filter shows 1/2 (50.00%). |
| 6. Reports | `F001` | Sidebar **Reports** → today to today, CS101 → **Generate report** → **Download CSV** and **Download PDF**. | A three-student report and two downloaded files. Faculty only see their own classes. |
| 7. Timetable and semester classes | `ADMIN1` | Sidebar **Timetable**; try adding MA101 to Section B on Monday period 4. Then **Semester classes**. | Six weekly classes by day. The duplicate is refused and the clash is named. Semester totals CS101 120 and MA101 40. |
| 8. Send login details | `ADMIN1` | Sidebar **Accounts and resets** → **Reset password** for S004 → type an email address under **Send these details by email** → **Send**. | "Login details sent to s***@…" (or printed in the terminal without Gmail). The address is saved on S004's account. |
| 9. Two-factor login | any | Log out and log in again with `OTP_REQUIRED=True`. | A QR code at first login, then 10 backup codes; later logins ask for the 6-digit code. |
| 10. Shortages and threshold | `ADMIN1` | Sidebar **Below threshold**, then **Attendance threshold** → 80 → **Save threshold**, and open the list again. | At 75%: S001 overall and in both subjects. At 80%: S001, S002 and S004 overall. The dashboard shortage box appears only while someone is below. |
| 11. Backup and recovery | `ADMIN1` | **Backup and recovery** → **Back up now** → **Download encrypted file**. Change the threshold to 85, then **Restore…** on that backup, enter your password, tick the confirmation → **Restore backup**. Log in again. | A completed, encrypted backup and a `.sambak` download. After the restore the threshold is back to 80; everyone is signed out and a safety backup was taken first. |
| 12. Permissions | `F001`, `S001` | Try to open `/students/create/`, `/timetable/` or `/backups/` as Faculty or Student. | Access is refused; nothing changes. The sidebar never shows these pages to them. |

Optional extras: **Forgot password?** on the login page (the Admin then sees "Reset requested" in **Accounts and resets**), adding a student or faculty member, and the 15-minute idle sign-out.

Recorded walkthroughs (made before the 9 November redesign) are in [demo/sprint-2](../demo/sprint-2/README.md) and [demo/sprint-1](../demo/sprint-1/README.md).

## 4. User guide by role

### Everyone

- **Log in** with your username (roll number, faculty ID or Admin username, any letter case) and password, then the 6-digit code from your authenticator app. No phone? Use **Email me a code** or one of your backup codes.
- **First login:** set up the authenticator app from the QR code, save the 10 backup codes (**Download as text file** or **Print**), then change your temporary password.
- **Forgot your password?** Use **Forgot password?** on the login page. The Admin is told, resets it, and a new temporary password is emailed to you.
- After 5 wrong passwords or 5 wrong codes, the account pauses for 15 minutes.
- **My profile** shows your own details and the college (PES University), read-only. **Change password** is on the same page.
- The **sidebar** lists only the pages your role can open; your name in the top bar opens **My profile**. **Log out** is at the top right. You are signed out automatically after 15 minutes without activity.

### Admin

| Task | Where (sidebar) |
|---|---|
| Add, edit, deactivate, reactivate or permanently delete students (a reason is required to delete) | **Students** |
| The same for faculty; faculty still teaching a class must be reassigned first | **Faculty** |
| Create sections ("Dept and sem", "Section", optional year), add subjects with their teacher, enroll students | **Classes and sections** |
| Create, rename, offer or delete subjects (a subject with attendance cannot be deleted) | **Subjects** |
| Weekly timetable: add a class by day and period (clashes are refused), remove it | **Timetable** |
| Classes each subject will hold this semester (drives the students' "classes needed" advice) | **Semester classes** |
| Reset a password, resend login details, reset someone's two-factor login, handle reset requests; email a temporary password with **Send** | **Accounts and resets** |
| Add another Admin | **Create Admin account** |
| Correct any record at any time, with a reason | **History and corrections** |
| Record a session faculty missed, with a reason | **Record missed attendance** |
| Reports with CSV/PDF export for any student, class or subject | **Reports** |
| See who is below the threshold, overall and per subject | **Below threshold** |
| Change the threshold (default 75%) or the faculty correction window (default 2 days, 0–30) | **Attendance threshold**, **Correction window** |
| Back up, schedule daily backups, download, import or restore | **Backup and recovery** |
| Today's classes across the college and which are marked | **Dashboard** |

### Faculty

| Task | Where (sidebar) |
|---|---|
| Today's classes, the next class and any class not yet marked | **Dashboard** |
| Mark attendance for an assigned class: every student must be marked; **Mark remaining as Present** fills the rest | **Mark attendance** (or the button beside a class on the dashboard) |
| See your classes, students and subjects | **My classes**, **Students in my classes**, **My subjects** |
| Correct a mark within the correction window (until 23:59 IST two days after the session, by default); older changes go to the Admin | **History and corrections** → **Apply filters** → **Correct** |
| Reports and CSV/PDF exports for your own classes | **Reports** |
| Students below the threshold in your subjects; you also get a Monday 08:00 email when the list is not empty | **Below threshold** |

### Student

| Task | Where (sidebar) |
|---|---|
| Overall attendance, subjects below the threshold and each subject's percentage | **Dashboard** |
| Attendance per subject with filters, what you need to reach the threshold, and each class marked Present or Absent (**View classes**) | **My attendance** |
| Where you stand now, the classes you need, and alerts when a subject or overall figure falls below the threshold (one alert per drop, also by email) | **Notifications** |
| Your roll number, section, subjects, teachers and college | **My profile** |

## 5. Requirement completion

All backlog items are Done on the project board. BL-32 is this handover; BL-35 to BL-40 record the 9 November additions.

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
| FR-10 Attendance history | BL-16, BL-39 | Complete | UC-11 |
| FR-11 Attendance calculation | BL-14 | Complete | UC-06, UC-08 |
| FR-12 Attendance reports | BL-20 | Complete | UC-09 |
| FR-13 Low-attendance detection | BL-22, BL-24 | Complete | UC-10 |
| FR-14 Notifications | BL-23 | Complete | UC-10 |
| FR-15 Search and filter | BL-19 | Complete | UC-11 |
| FR-16 Report export | BL-21 | Complete | UC-09 |
| FR-17 Dashboards (and My profile) | BL-25, BL-35, BL-39 | Complete | UC-12 |
| FR-18 Modification history | BL-18 | Complete | UC-07 |
| FR-19 Backup and recovery | BL-26, BL-27 | Complete | UC-13 |
| FR-20 Logout | BL-06 | Complete | UC-12 |
| FR-21 Two-factor login | BL-33 | Complete | UC-01 |
| FR-22 Timetable and class reminders | BL-36 | Complete | UC-14 |
| FR-23 Semester classes and attendance advice | BL-37 | Complete | UC-14, UC-08, UC-10 |
| FR-24 Send login details by email | BL-34, BL-38 | Complete | UC-01 |

| Requirement | Status | Basis |
|---|---|---|
| NFR-01 Performance | Met locally | PT_01–PT_03 passed with 50 users on one machine on 9 Nov; repeat on the real server |
| NFR-02 to NFR-04 Security, authentication, authorization | Met | BL-05, BL-31; UC-01 and integration tests |
| NFR-05 Reliability, NFR-10 Data integrity | Met | BL-13 duplicate/partial-save protection; atomic corrections and restore |
| NFR-06 Availability | Not measured | Needs a month of monitoring on a deployed server (VAL-02) |
| NFR-07 Usability | Met | BL-30 manual workflow review, the 9 November redesign (BL-35) and automated checks |
| NFR-08 Scalability | Met locally | PT_04: 1,000 students, 750,000 marks, 50 users |
| NFR-09 Maintainability | Met | Ruff lint/format, 556 automated tests (9 Nov), 95.10% line and 90.78% branch coverage |
| NFR-11 Privacy, NFR-14 Auditability | Met | Role-scoped data, owner-only credential email, audit log |
| NFR-12 Compatibility | Partly verified | Chromium, Firefox and WebKit at 1440, 768 and 320 px (9 Nov); Edge, branded Safari and real phones not tested (VAL-03) |
| NFR-13 Backup and recovery | Met on macOS | Windows-only file-permission checks not run (VAL-04) |
| NFR-15 Accuracy | Met | All calculation tests pass |

## 6. Where the evidence is

| What | Where |
|---|---|
| Requirements, design, use cases, test plan, security requirements | [Documents/](.) (SRS v2.1, Software_Architecture_Design(SAD) v1.1, Use_Case_Flow, Test_Plan_Document v2.1, Security_Requirements_Specification) |
| Changes from the original SRS and design, for the demo | [Changes_from_Original_Design.md](Changes_from_Original_Design.md) |
| Agreed rules and decisions (D-01 to D-28) | [BL-01_Decision_Log.md](BL-01_Decision_Log.md) |
| Part 3 test reports and the 224-case Test Case Document | [docs/](../docs/README.md) |
| Performance, browser and recovery verification records | [Documents/Verification/](Verification/) |
| Implementation notes per backlog item | `Documents/BL-*_Implementation.md` and related notes |
| Sprint demo videos | [demo/](../demo/) |
| Running the tests | `python manage.py test`, `ruff check .` (README, "Running tests and checks") |

## 7. Known limitations and non-blocking issues

None of these blocks the demonstration.

1. **Availability (NFR-06) is not measured.** It needs a month of monitoring on a real server during 08:00–18:00, Monday–Saturday.
2. **Browser and device coverage is partial.** Edge, branded Safari, the full "latest two versions" matrix and real Android/iOS phones were not tested; phone widths (320 and 360 px) were emulated.
3. **Windows backup checks were not run.** Three file-permission tests only run on Windows. They account for most of the code not yet covered by tests.
4. **Performance was measured on one machine.** Repeat PT_01–PT_04 on the real server; network, HTTPS and email delays were not included.
5. **Email needs local setup.** Each machine needs its own Gmail app password in `.env`. The demo accounts have no email addresses, so alert emails, login-detail emails and emailed login codes only reach someone after a real address is added.
6. **Scheduled jobs need the server's scheduler.** Daily backups (`run_scheduled_backups`, every minute) and the Monday faculty email (`send_weekly_shortage_emails`) only run if cron or Task Scheduler calls them. Setting the time in the app does not install a scheduler.
7. **Password reset goes through the Admin.** There are no self-service reset links (BL-01 D-23), and a temporary password stays valid until it is used or replaced.
8. **Only Present and Absent exist.** "Late" and partial credit were deferred (D-06).
9. **Faculty corrections have a deadline.** After the window (default 2 days), only the Admin can correct or add a session, with a reason.
10. **Restoring a backup signs everyone out** and cancels emailed codes and backup codes; the restore needs a maintenance window. Backups over 256 MiB are refused, and connection poolers in transaction mode are not supported.
11. **The demo data is small.** It is for functional demos; the 1,000-student capacity data is generated separately by the BL-29 verification tools.
12. **Timetable and semester totals are entered by hand.** The Admin enters them; there is no automatic timetable generation or import, and the class reminders appear only on the dashboard (no email or push reminder).
