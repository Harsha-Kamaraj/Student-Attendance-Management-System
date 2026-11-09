# Changes from the Original SRS and Design

Student Attendance Management System · PES University · prepared for the Sprint 2 demonstration · 9 November 2026

This page lists every way the finished system differs from the original Part 1 documents (SRS v1.0, the Security Requirements Specification, the use case diagram and the component design), why each change was made, and where it is now documented. Every change was agreed by the team and recorded in the [BL-01 decision log](BL-01_Decision_Log.md). The Part 1 documents have been updated to match, so they describe the system as built: [SRS v2.0](Software_Requirements_Specification(SRS).docx), [Test Plan v2.0](Test_Plan_Document.docx), [SAD](Software_Architecture_Design(SAD).docx) and [Use Case Flow](Use_Case_Flow.docx).

## What did not change

- **Architecture:** the layered Django web application with the components in the original component diagram (Web Interface, gateway, User & Auth, Academic Management, Attendance, Report, Notification, Backup & Recovery, Audit, Data Access).
- **Use cases UC-01 to UC-13** and their actors.
- **Requirements FR-01 to FR-19 and NFR-01 to NFR-15:** none was removed, and every ID is unchanged.
- **The attendance rules:** Present/Absent only, complete submissions, the correction window, the percentage formulas and the threshold.

## Changes made after the original documents

| # | Change | Original documents said | What was built | Why | Decision | Where documented |
|---|---|---|---|---|---|---|
| 1 | **Two-factor login** (new) | Password login only. | After the password, every user enters a 6-digit code from an authenticator app; an emailed code and 10 one-time backup codes are fall-backs; 5 wrong codes lock the account for 15 minutes. | Protects accounts if a password is guessed or stolen (TH-01, TH-02). | D-20 to D-22 | FR-21, SEC-29 to SEC-32, UC-01, SAD SD-1 |
| 2 | **Forgotten passwords** | SEC-07: a self-service reset link valid for 30 minutes. | "Forgot password?" asks the Admins to reset; the Admin issues a temporary password that is emailed only to the owner. | A self-service link conflicted with Admin-controlled accounts (D-02). | D-23 | SEC-07, FR-01 criterion 5, UC-01 2a |
| 3 | **Login details by email** (new) | The Admin hands each temporary password over in person. | New and reset accounts receive their username, temporary password and login link by email; on failure the Admin sees the password once, and can now send it from the same page to an address they enter. | Saves handing passwords over by hand; keeps passwords out of logs and the Admin's records. | BL-34, D-26 | FR-24, SEC-06, UC-01/02/03 addendum |
| 4 | **Weekly timetable and class reminders** (new) | No timetable. | The Admin keeps a weekly timetable; Faculty and Admin dashboards show today's classes, the next class, and classes not yet marked. | Unmarked classes were the main cause of missing attendance. | D-24 | FR-22, UC-14 |
| 5 | **Semester classes and attendance advice** (new) | Students saw only a percentage. | The Admin may set classes per subject this semester; students see how many classes they must attend to reach the threshold, in the dashboard, the attendance page and alerts. Students can open a subject to see each class marked. | A percentage alone does not tell a student what to do. | D-25 | FR-23, FR-09 c4, FR-14 c5, UC-08, UC-10 |
| 6 | **Section batch year, section deletion and My profile** | Sections had a name only; no profile page. | Sections can carry a batch year and be edited or deleted while unused; every user has a read-only My profile page (showing the college). | Requested during Sprint 2 testing (31 Oct). | — | FR-06 c4–5, FR-17 c3 |
| 7 | **Reports need an explicit scope and date range** | Report scope was optional. | A report is generated only after a scope and date range are chosen. | Stops an accidental report of every record (#51). | — | FR-12, UC-09 |
| 8 | **History after filtering** | History listed every record on opening. | Records appear once the filters are applied; applying with no filters lists everything in scope. | Requested during review: opens on the filters, not a long list. | D-27 | FR-10 c4, UC-11 |
| 9 | **Dashboard counts and interface** | — | Shortage counts skip deactivated students and match the list; the summary appears only when someone is below the threshold. New logo, role-based sidebar, split sign-in page, buttons for every action. | A count did not match its list; usability review (NFR-07). | D-28 | FR-17 c4–5, UC-12 |

## Design (SAD) refinements

| Original design element | As built | Why |
|---|---|---|
| API Gateway as a separate component | Django's URL dispatcher and middleware stack (security headers, sessions, CSRF, login required, OTP gate, forced password change, restore lock). | Same responsibilities without another server to run and secure. |
| Email Provider | Any SMTP service configured in `.env` (Gmail in the project setup); development prints emails to the terminal. | Standard, provider-independent. |
| Backup Scheduler | The `run_scheduled_backups` command run by cron or Task Scheduler. | Simpler than a background service; the same code as manual backups. |
| Notification Service weekly list | The `send_weekly_shortage_emails` command, once per faculty member per week. | A re-run cannot send duplicates. |
| New in the Academic Management component | Timetable and semester class totals (`academics.planning_views`, `TimetableSlot`). | Supports changes 4 and 5. |

## Clarifications before development (not deviations)

Before any code was written, decisions D-01 to D-19 resolved conflicts and unclear wording in the original SRS. They covered:
- who manages students, accounts, deletion, subject deletion and enrolment
- attendance statuses, complete submissions and the session key
- the correction window, percentage formulas, zero classes and rounding
- the threshold, notifications and the faculty list
- measurable quality targets and alignment with the security specification

These were folded into SRS v1.0 itself, so the system follows them as written.

## Known limitations

See section 7 of the [demonstration and handover guide](BL-32_Demo_and_Handover.md). The main ones:
- There is no "Late" status (D-06).
- There is no self-service password reset (D-23).
- Email delivery depends on the SMTP settings in `.env`.
- Windows-only backup storage code is measured separately for coverage.

## Explaining the changes in the demo

1. Open with: "The architecture and the 13 original use cases are as designed. Every change is in the decision log, and the documents were updated to match."
2. Show the additions in this order:
   - two-factor login (UC-01)
   - today's classes on the Faculty dashboard (UC-14)
   - a student's subject cards, "classes needed" and class-by-class list (UC-08)
   - the Send button on a password reset (FR-24)
3. For each one, say why it was added, using the "Why" column above, and name its requirement ID.
4. If asked about the gateway: the logical gateway is Django's middleware stack (SAD section 5.1).
