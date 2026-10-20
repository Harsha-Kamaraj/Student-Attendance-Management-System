# Student-Attendance-Management-System
Software Engineering Project

A web application for recording, correcting and reporting student attendance, with Admin, Faculty and Student roles. Requirements, use cases, test plan and security requirements are in [`Documents/`](Documents/); the agreed attendance rules are in [`Documents/BL-01_Decision_Log.md`](Documents/BL-01_Decision_Log.md).

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

- There is no self-registration. The Admin creates every account at **Dashboard → Create account** (`/users/create/`) by entering a username (roll number or faculty ID), role and email.
- The system shows a one-time temporary password to the Admin, who passes it to the user. The user must change it at first login.
- Passwords need at least 8 characters with an upper-case letter, a lower-case letter, a digit and a special character.
- After 5 wrong passwords in a row, login is blocked for 15 minutes. The Admin can reset a password (`/users/`), which also removes the block.
- Logins, account creation, password changes and resets are recorded in the audit log.

## Configuration variables

All settings that differ between machines are read from `.env` (or real environment variables).

| Variable | Required | Purpose | Example |
|---|---|---|---|
| `SECRET_KEY` | Yes | Signs sessions and security tokens. Keep it secret. | long random string |
| `DATABASE_URL` | Yes | PostgreSQL connection | `postgres://attendance_app:PASSWORD@localhost:5432/attendance_dev` |
| `DEBUG` | No (default `False`) | Detailed error pages; `True` only on your own machine | `True` |
| `ALLOWED_HOSTS` | No (default empty) | Comma-separated host names | `localhost,127.0.0.1` |
| `SECURE_COOKIES` | No (default `False`) | Send cookies only over HTTPS; `True` in production | `False` |

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
