# Student-Attendance-Management-System
Software Engineering Project

A web application for recording, correcting and reporting student attendance, with Admin, Faculty and Student roles. Requirements, use cases, test plan and security requirements are in [`Documents/`](Documents/); the agreed attendance rules are in [`Documents/BL-01_Decision_Log.md`](Documents/BL-01_Decision_Log.md).

## Session security (BL-06)

- Signed-in users log out with the CSRF-protected **Log out** button in the navigation bar (`POST /logout/`). Logout invalidates the current Django session and redirects to `/login/`.
- Sessions expire after **15 minutes of inactivity**. Django refreshes the expiry on active requests (`SESSION_COOKIE_AGE=900` and `SESSION_SAVE_EVERY_REQUEST=True`).
- Protected pages require a fresh login after logout or session expiration. Dashboard and account list responses use `Cache-Control: no-store` to discourage stale private pages appearing on browser Back.
- Tests: `python manage.py test apps.accounts.test_sessions`.

## Technology

| Part | Choice |
|---|---|
| Language | Python 3.12 or newer (developed and tested on 3.14) |
| Web framework | Django 5.2 LTS (security support until April 2028) |
| Database | PostgreSQL 16 or newer (developed on 18) |
| Pages | Django templates with Bootstrap 5 |
| Code style | Ruff (linter and formatter) |

## Setup

These steps work on macOS and Linux. Windows differences are noted.

**1. Install prerequisites:** Python 3.12+, PostgreSQL 16+ and Git. On macOS with Homebrew:

```bash
brew install python postgresql@18
brew services start postgresql@18
```

**2. Clone the repository and create a virtual environment:**

```bash
git clone https://github.com/Harsha-Kamaraj/Student-Attendance-Management-System.git
cd Student-Attendance-Management-System
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
```

**3. Create a database user and the development database.** Choose your own password. `CREATEDB` lets the test runner create its temporary test database.

```bash
psql -d postgres -c "CREATE ROLE attendance_app LOGIN CREATEDB PASSWORD 'choose-a-password';"
createdb -O attendance_app attendance_dev
```

**4. Create your local configuration:**

```bash
cp .env.example .env               # Windows: copy .env.example .env
```

Edit `.env`: set `SECRET_KEY` (the file shows how to generate one) and put your password in `DATABASE_URL`. Never commit `.env`; it is listed in `.gitignore`.

**5. Create the tables and an Admin account, then start the server:**

```bash
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Open http://127.0.0.1:8000/login/ and log in with the Admin account you just created. Usernames ignore upper and lower case (they are stored in capitals). The Django admin site is at http://127.0.0.1:8000/admin/.

## Accounts and login

- There is no self-registration. The Admin adds students at **Manage students** and faculty at **Manage faculty**; each gets a login (username = roll number or faculty ID). Further Admin accounts are created at **Create Admin account** (`/users/create/`).
- The system shows a one-time temporary password to the Admin, who passes it to the user. The user must change it at first login.
- Passwords need at least 8 characters with an upper-case letter, a lower-case letter, a digit and a special character.
- After 5 wrong passwords in a row, login is blocked for 15 minutes. The Admin can reset a password (`/users/`), which also removes the block.
- Logins, account creation, password changes and resets are recorded in the audit log.

## Two-factor login (BL-33)

After the password, every user enters a one-time code:

- **First login:** scan the QR code with an authenticator app (Google Authenticator, Microsoft Authenticator) and enter the 6-digit code. Save the 10 backup codes shown afterwards — each works once.
- **Every login:** enter the current code from the app. No phone? Click **Email me a code** (valid 10 minutes, at most 3 per 15 minutes) or use a backup code.
- 5 wrong codes lock the account for 15 minutes. An Admin can reset someone's two-factor login at **Accounts → Reset OTP** after re-entering their own password.
- The same attempt limit applies during initial setup. Resetting OTP invalidates all of that user's existing sessions and recovery codes; they must log in and enroll again.
- During development, emails are printed in the terminal running the server.
- For real email delivery, set `EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend` and configure the `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, and TLS/SSL values shown in `.env.example`. If delivery fails, the login page offers the authenticator and backup-code alternatives.
- To try the app on your own machine without a phone, add `OTP_REQUIRED=False` to your `.env` and restart the server. Never do this on a shared or production server.

When upgrading an existing checkout, install `requirements-dev.txt` and run `python manage.py migrate` before starting the server. The OTP session-invalidation migration signs existing sessions out.

OTP regression checks: `python manage.py test apps.accounts.test_otp apps.accounts.test_otp_concurrency`. These enable OTP explicitly and cover the complete login flow, replay prevention, lockouts, recovery, CSRF, session invalidation, and concurrent requests against PostgreSQL. The test runner disables OTP for older tests that exercise other features with password-only test logins.

## Attendance percentages (BL-14)

Students open **View my attendance percentages** from their dashboard (`/attendance/mine/`). Each subject shows attended/held counts and a percentage rounded half up to two decimals. Overall attendance pools the counts: `10/12 + 8/10 = 18/22 (81.82%)`. Subjects without recorded classes show **N/A – no classes yet**. Totals use current saved records and update automatically after new marks or valid corrections. See [`Documents/BL-14_Percentage_Calculation.md`](Documents/BL-14_Percentage_Calculation.md).

## Attendance history and corrections (BL-16 to BL-18)

Admin and Faculty open **Attendance history and corrections** from their dashboard to filter saved records, correct a status, or view its modification history. Faculty can correct only assigned classes within the default two-calendar-day window ending at 23:59:59 IST. Admin corrections always require a reason and are logged as overrides. Admin can configure the window from 0–30 days at **Configure faculty correction window**; it also controls recording missed sessions.

Each correction and its editor, timestamp, old/new status and reason are saved atomically. Percentages and dashboards reflect the saved correction immediately. Students see their own updated totals, while staff history remains restricted to Admin and authorized Faculty. Run `python manage.py migrate` before using these pages. See [`Documents/BL-16-18_Implementation.md`](Documents/BL-16-18_Implementation.md).

## Low-attendance notifications and the below-threshold list (BL-23, BL-24)

- **Students** get one in-app notification (**Notifications** in the navigation bar) and one email each time a subject or overall percentage falls below the threshold. Nothing more is sent while it stays below; recovering to the threshold or above clears it, and a later drop notifies again. The check runs after every attendance save, correction and threshold change. If email fails, the in-app notification is still delivered and the failure is logged.
- **Admin and Faculty** open **Students below threshold** from the dashboard (`/attendance/shortages/`). Faculty see only their assigned subjects; the Admin also sees overall percentages. The list is always current.
- **Monday email:** schedule `python manage.py send_weekly_shortage_emails` for Mondays at 08:00 IST (cron example in the implementation note). Faculty with an empty list get no email, and re-running in the same week sends no duplicates.

Run `python manage.py migrate` before using these pages. See [`Documents/BL-23-24_Implementation.md`](Documents/BL-23-24_Implementation.md).

## Backup and recovery (BL-26 / BL-27)

These features are independent of low-attendance notifications and lists (BL-23/24).
Admins open **Backup and recovery** from their dashboard (`/backups/`).

- **Back up now** creates an authenticated-encrypted snapshot of users, academics, attendance, application settings, permissions and audit history. Files are private (`0600`) in `BACKUP_DIRECTORY` (`0700`, default `var/backups`, excluded from Git). A failed backup never overwrites an older one.
- **Configure schedule** enables a daily time in IST. The server scheduler must invoke `run_scheduled_backups` every minute (see below). Missed runs catch up once; failures retry after 15 minutes. The page shows the next attempt, last scheduled success and failures.
- **Download encrypted file** lets the Admin keep an off-server copy. **Import a saved backup** validates a downloaded `.sambak` file and adds it to the catalogue without changing application data.
- **Restore** requires the Admin's current password and explicit confirmation. Integrity and schema checks run first; a safety backup is required before replacement. Restore commits all data together or rolls back. Live requests are blocked during recovery, and an active request causes restore to ask the Admin to retry.
- Existing audit events and the backup catalogue/schedule survive restore. Missing audit events from the snapshot are appended. All sessions end, and previously issued email/backup codes are invalidated; sign in with an account/password from the snapshot and a fresh authenticator code or new email code. Admin OTP reset can issue a replacement set of backup codes.

After installing dependencies and running migrations, generate a Fernet key and put it in the local `.env` as `BACKUP_ENCRYPTION_KEY`. Keep a secure copy of the key separately from backup files. A missing key disables backup creation; there is no unencrypted fallback.

Configure the **server's** task scheduler to run the following every minute, as the application OS user. Example crontab (replace paths for your deployment):

```cron
* * * * * cd /srv/attendance && /srv/attendance/.venv/bin/python manage.py run_scheduled_backups >> /srv/attendance-backup-scheduler.log 2>&1
```

Setting a time in the web page does not install a system scheduler. To check one tick manually:

```bash
python manage.py run_scheduled_backups
```

For recovery onto a replacement server, deploy the same application release and migrations, configure PostgreSQL and the original encryption key, create a temporary Admin and complete OTP setup, then import and restore a saved encrypted file. Restoring replaces the temporary Admin too; use an Admin account from the snapshot afterward. Backups from a different migration/schema version are rejected. `.env`, encryption keys, application source, sessions and external files are not part of the data snapshot.

Snapshots are processed in memory with a configurable 256 MiB file limit; provision sufficient worker memory and request timeouts. Backup operations require a direct or session-pooled PostgreSQL connection because maintenance locks span transactions. Do not use transaction-pooling mode. Database table locks also protect consistency from external writers; run recovery during a maintenance window and stop external jobs that write application data.

Tests: `python manage.py test apps.backups` (uses only disposable test databases and temporary encrypted storage).

## Configuration variables

All settings that differ between machines are read from `.env` (or real environment variables).

| Variable | Required | Purpose | Example |
|---|---|---|---|
| `SECRET_KEY` | Yes | Signs sessions and security tokens. Keep it secret. | long random string |
| `DATABASE_URL` | Yes | PostgreSQL connection | `postgres://attendance_app:PASSWORD@localhost:5432/attendance_dev` |
| `DEBUG` | No (default `False`) | Detailed error pages; `True` only on your own machine | `True` |
| `ALLOWED_HOSTS` | No (default empty) | Comma-separated host names | `localhost,127.0.0.1` |
| `SECURE_COOKIES` | No (default `False`) | Send cookies only over HTTPS; `True` in production | `False` |

## Test data

To try the app with realistic fictional data (Admin, 3 faculty, 4 students, 2 sections, 2 subjects, 103 attendance sessions), run on a development database:

```bash
python manage.py seed_test_data
```

All accounts use the password `Attend#2026` (for example `ADMIN1`, `F001`, `S001`). The command only runs when `DEBUG=True` and refuses to run twice. The data and the figures it produces are described in [`Documents/Test_Data_Fixture.md`](Documents/Test_Data_Fixture.md).

## Running tests and checks

```bash
python manage.py test              # all tests (uses a temporary test database)
ruff check .                       # code problems
ruff format .                      # format code (use --check to only report)
```

GitHub Actions runs the same checks and tests on every push to `main` and on every pull request (`.github/workflows/ci.yml`).

## Project structure

```
config/           Project settings, URL routes, project-level tests
apps/
  accounts/       User accounts, roles and login           (BL-04 to BL-06)
  academics/      Students, faculty, subjects, sections    (BL-07 to BL-11)
  attendance/     Attendance sessions and corrections      (BL-12 to BL-17)
  audit/          Audit history                            (BL-18)
  notifications/  Low-attendance alerts and shortage list  (BL-23, BL-24)
templates/        Shared page layouts
static/           Shared CSS, JavaScript and images
Documents/        SRS, use cases, test plan, security requirements, diagrams
```

Built-in project settings that come from the agreed requirements:

- Time zone is India Standard Time (`Asia/Kolkata`), used for attendance dates and the correction window (BL-01 D-09).
- Sessions expire after 15 minutes of inactivity (SEC-08).
- Passwords are stored only as salted hashes (SEC-05).
- The project uses its own user model (`accounts.User`) so roles can be added without rebuilding the database.

## Adding a dependency

Install it in the virtual environment, then add it with an exact version (`package==x.y.z`) to `requirements.txt` (needed to run the app) or `requirements-dev.txt` (development tools only).
