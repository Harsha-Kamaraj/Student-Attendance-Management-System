"""
Django settings for the Student Attendance Management System.

Values that differ between machines (secret key, database, debug mode) are
read from environment variables or a local `.env` file. See `.env.example`.
"""

from pathlib import Path

import environ

BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env(
    DEBUG=(bool, False),
    ALLOWED_HOSTS=(list, []),
    SECURE_COOKIES=(bool, False),
    OTP_REQUIRED=(bool, True),
)
environ.Env.read_env(BASE_DIR / ".env")

SECRET_KEY = env("SECRET_KEY")
DEBUG = env("DEBUG")
ALLOWED_HOSTS = env("ALLOWED_HOSTS")


# Application definition

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "apps.accounts",
    "apps.academics",
    "apps.attendance",
    "apps.audit",
    "apps.notifications",
    "apps.backups",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "apps.backups.middleware.RestoreMaintenanceMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.auth.middleware.LoginRequiredMiddleware",  # login needed unless marked public (SEC-01)
    "django.contrib.messages.middleware.MessageMiddleware",
    "apps.accounts.middleware.OTPRequiredMiddleware",  # one-time code after the password (SEC-29)
    "apps.accounts.middleware.ForcePasswordChangeMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "apps.notifications.context_processors.unread_notifications",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"


# Database (PostgreSQL), e.g. postgres://user:password@localhost:5432/attendance_dev

DATABASES = {"default": env.db("DATABASE_URL")}


# Authentication

AUTH_USER_MODEL = "accounts.User"
AUTHENTICATION_BACKENDS = ["apps.accounts.backends.AccountBackend"]
LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "dashboard"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
    {"NAME": "apps.accounts.validators.PasswordComplexityValidator"},  # SEC-04
]


# Sessions: expire after 15 minutes of inactivity (SEC-08)

SESSION_COOKIE_AGE = 15 * 60
SESSION_SAVE_EVERY_REQUEST = True
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SECURE = env("SECURE_COOKIES")
CSRF_COOKIE_SECURE = env("SECURE_COOKIES")


# Internationalization: all attendance dates and the correction window use IST (BL-01 D-09)

LANGUAGE_CODE = "en-us"
TIME_ZONE = "Asia/Kolkata"
USE_I18N = True
USE_TZ = True


# Static files (CSS, JavaScript, Images)

STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# Two-factor login (BL-33, SEC-29 to SEC-32). On by default; set OTP_REQUIRED=False in a local .env
# only to try the app without an authenticator app during development.

OTP_REQUIRED = env("OTP_REQUIRED")
TEST_RUNNER = "config.test_runner.Runner"


# Email: printed to the terminal by default; set the SMTP backend and credentials for delivery.

EMAIL_BACKEND = env("EMAIL_BACKEND", default="django.core.mail.backends.console.EmailBackend")
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", default="Student Attendance <noreply@attendance.local>")
EMAIL_HOST = env("EMAIL_HOST", default="localhost")
EMAIL_PORT = env.int("EMAIL_PORT", default=25)
EMAIL_HOST_USER = env("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", default="")
EMAIL_USE_TLS = env.bool("EMAIL_USE_TLS", default=False)
EMAIL_USE_SSL = env.bool("EMAIL_USE_SSL", default=False)
EMAIL_TIMEOUT = env.int("EMAIL_TIMEOUT", default=10)
SITE_URL = env("SITE_URL", default="http://127.0.0.1:8000" if DEBUG else "")

# Encrypted backups (BL-26/27). Keep the key separately from copies of the backup files.
BACKUP_DIRECTORY = Path(env("BACKUP_DIRECTORY", default=str(BASE_DIR / "var" / "backups")))
BACKUP_ENCRYPTION_KEY = env("BACKUP_ENCRYPTION_KEY", default="")
BACKUP_MAX_BYTES = env.int("BACKUP_MAX_BYTES", default=256 * 1024 * 1024)
BACKUP_LOCK_TIMEOUT_SECONDS = env.int("BACKUP_LOCK_TIMEOUT_SECONDS", default=10)
