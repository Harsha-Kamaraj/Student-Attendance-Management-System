# BL-23 and BL-24 — Low-attendance notifications and the below-threshold list

Backlog items: BL-23 (#23, FR-14) and BL-24 (#24, FR-13) · Use case UC-10 · Rules BL-01 D-11, D-13, D-14, D-15, D-03.

## BL-23 — Student notification

| Acceptance criterion | How it is met |
|---|---|
| Notification through the agreed channel | In-app notification (**Notifications** in the navigation bar, `/notifications/`) and an email to the student's account address (D-14). |
| Identifies the shortage clearly | The message lists each subject and/or the overall figure that fell below, as `attended/held (percentage)`, and the threshold. |
| Frequency without unintended duplicates | `ShortageFlag` stores what is currently below for each student (one row per subject, one for overall). A notification is created only for a flag that did not exist. Several percentages dropping in one save produce one notification. Students are row-locked during evaluation, so concurrent saves cannot notify twice. |
| Boundary rule | `attended × 100 < threshold × held`; equal is not below; no classes is never flagged (D-11, D-13). |
| Stops after recovery | Recovering to ≥ threshold deletes the flag and sends nothing. A later drop notifies again (UC-10 3a). |
| Only the affected student | The notification and email go to that student's account only. The inbox shows only the signed-in student's notifications; staff get 403 (permission `notifications.view`, Students only). |

When the check runs: after every attendance submission, every correction, and every threshold change (which re-evaluates all active students). It runs inside the same database transaction as the change. Emails are sent after the transaction commits, so a rejected save sends nothing. If the email fails (or the account has no email address), the in-app notification is kept and an audit entry `notification.email_failed` is written (D-14, UC-10 4b). Deactivated students are not evaluated (D-03).

## BL-24 — Below-threshold list for Admin and Faculty

| Acceptance criterion | How it is met |
|---|---|
| Students below the configured/default threshold | `/attendance/shortages/` (**Students below threshold** on the dashboards), using the same exact comparison. |
| Identifies the student and percentage or subject | Roll number, name, class/section, subject and `attended/held (percentage)`. The Admin also sees overall percentages. |
| Changes and corrections refresh the list | Calculated from saved records on every request; nothing is cached. |
| Recovered students leave the list | Only students currently below are listed. |
| Authorized scope | Permission `low_attendance.view` (Admin, Faculty). Faculty see only their assigned subjects, and only classes they teach are counted. Overall rows are Admin-only, because an overall figure includes other faculty members' classes. Deactivated students are left out. |
| Empty list message | "No students are currently below the 75% threshold …". |
| Monday 08:00 email; none when empty | `python manage.py send_weekly_shortage_emails`. Each active faculty member with a non-empty list gets one email of their own students. At most one per faculty member per week (`WeeklyShortageEmail`), so re-running is safe; a failed send is logged (`notification.weekly_email_failed`) and retried on the next run. |

### Scheduling the Monday email

The project has no background worker, so the server's cron runs the command:

```cron
CRON_TZ=Asia/Kolkata
0 8 * * 1  cd /path/to/Student-Attendance-Management-System && .venv/bin/python manage.py send_weekly_shortage_emails
```

Email delivery uses the existing `EMAIL_*` settings (printed to the terminal by default).

## Tests

`python manage.py test apps.notifications` — covers UT_10_1 to UT_10_8, IT_10_4 to IT_10_6, ST_10_1 to ST_10_6, scope, privacy, empty list, weekly de-duplication and email failure.
