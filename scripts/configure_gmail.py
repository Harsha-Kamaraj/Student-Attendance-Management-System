"""Configure only the local email settings; prompts never put the password in chat."""

import getpass
import os
import re
import subprocess
import sys
import warnings
from email.utils import parseaddr
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
PYTHON = Path(sys.executable)
ENV_FILE = PROJECT / ".env"


def update_settings(text, settings):
    remaining = dict(settings)
    lines = []
    for line in text.splitlines():
        match = re.match(r"^\s*(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=", line)
        key = match.group(1) if match else None
        if key in settings:
            if key in remaining:
                lines.append(key + "=" + remaining.pop(key))
        else:
            lines.append(line)
    if remaining:
        lines += ["", "# Local Gmail delivery settings. Never commit this file."]
        lines += [key + "=" + value for key, value in remaining.items()]
    return "\n".join(lines).rstrip() + "\n"


def main():
    if not sys.stdin.isatty():
        print("Open this setup in a local terminal so the password can be hidden.")
        return 1
    if not ENV_FILE.is_file() or not PYTHON.is_file():
        print("Create .env from .env.example and configure your database first. No settings changed.")
        return 1
    print("Project: " + str(PROJECT))
    print("Use a Gmail/Google Workspace account you control, with an App password.")
    address = input("Sending Gmail address: ").strip()
    if parseaddr(address)[1] != address or not re.fullmatch(
        r"[A-Za-z0-9._+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", address
    ):
        print("Enter a complete email address. No settings changed.")
        return 1
    warnings.simplefilter("error", getpass.GetPassWarning)
    try:
        password = getpass.getpass("16-character Google App password (hidden): ")
    except getpass.GetPassWarning:
        print("This terminal cannot hide the password. No settings changed.")
        return 1
    password = "".join(password.split())
    if not re.fullmatch(r"[A-Za-z0-9]{16}", password):
        print("Use the 16-character App password from Google. No settings changed.")
        return 1
    settings = {
        "EMAIL_BACKEND": "django.core.mail.backends.smtp.EmailBackend",
        "EMAIL_HOST": "smtp.gmail.com",
        "EMAIL_PORT": "587",
        "EMAIL_USE_TLS": "True",
        "EMAIL_USE_SSL": "False",
        "EMAIL_HOST_USER": address,
        "EMAIL_HOST_PASSWORD": password,
        "DEFAULT_FROM_EMAIL": "Student Attendance <" + address + ">",
        "EMAIL_TIMEOUT": "15",
    }
    # Existing database, application secrets, OTP and backup settings are preserved.
    updated = update_settings(ENV_FILE.read_text(encoding="utf-8-sig"), settings)
    ENV_FILE.write_text(updated, encoding="utf-8")
    print("Saved Gmail settings in the ignored local .env. The password was not displayed.")
    recipient = input("Test recipient (Enter = your sending address; 'skip' = no email): ").strip()
    if recipient.lower() == "skip":
        print("Test email skipped. Restart your server to apply the settings.")
        return 0
    recipient = recipient or address
    if parseaddr(recipient)[1] != recipient or not re.fullmatch(
        r"[A-Za-z0-9._+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", recipient
    ):
        print("Invalid test recipient. Settings saved; no email sent.")
        return 1
    # Match the saved settings even if this terminal has older email overrides.
    child_env = dict(os.environ)
    child_env.update(settings)
    result = subprocess.run(
        [str(PYTHON), "manage.py", "sendtestemail", "--", recipient],
        cwd=PROJECT,
        env=child_env,
        capture_output=True,
        text=True,
    )
    if result.returncode:
        failure = re.search(
            r"\b(SMTP\w*Error|TimeoutError|ConnectionRefusedError|SSLError|gaierror|"
            r"ModuleNotFoundError|ImproperlyConfigured)\b",
            result.stderr,
        )
        print("Test email failed" + (": " + failure.group(1) if failure else "") + ". Settings remain saved.")
        print("Check the App password, account restrictions and internet connection.")
        return 1
    print("Django submitted the test email successfully. Check your inbox and Spam folder.")
    print("Restart the attendance server to use these saved settings.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (KeyboardInterrupt, EOFError):
        print("\nSetup stopped. Check your saved settings and inbox before retrying.")
        raise SystemExit(1) from None
