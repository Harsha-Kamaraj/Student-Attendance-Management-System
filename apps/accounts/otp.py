"""Two-factor login with one-time codes (BL-33; SEC-29 to SEC-32; BL-01 D-20 to D-22).

After the password, every user enters a 6-digit code from an authenticator app (main method),
a code sent by email (backup), or one of 10 single-use backup codes.
"""

import secrets
import uuid
from datetime import timedelta
from smtplib import SMTPException

import pyotp
import qrcode
import qrcode.image.svg
from django.conf import settings
from django.contrib.auth.hashers import check_password, make_password
from django.core.mail import send_mail
from django.db import transaction
from django.utils import timezone

from apps.audit import services as audit

from .models import OTPBackupCode, OTPEmailCode, User
from .services import LOCKOUT_DURATION

ISSUER = "Student Attendance"
SESSION_VERIFIED = "otp_verified"
SESSION_SETUP_SECRET = "otp_setup_secret"

MAX_FAILED_CODES = 5  # SEC-32
BACKUP_CODE_COUNT = 10  # SEC-31
EMAIL_CODE_LIFETIME = timedelta(minutes=10)  # SEC-32
EMAIL_CODE_LIMIT = 3  # emailed codes per window (SEC-32)
EMAIL_CODE_WINDOW = timedelta(minutes=15)
_BACKUP_ALPHABET = "abcdefghjkmnpqrstuvwxyz23456789"  # no look-alike characters


class TooManyEmailCodes(Exception):
    pass


class NoEmailAddress(Exception):
    pass


class AccountLocked(Exception):
    pass


class AlreadyConfigured(Exception):
    pass


class EmailDeliveryFailed(Exception):
    pass


# --- Authenticator app ------------------------------------------------------------------


def new_secret():
    return pyotp.random_base32()


def provisioning_uri(user, secret):
    return pyotp.TOTP(secret).provisioning_uri(name=user.username, issuer_name=ISSUER)


def qr_code_svg(uri):
    """An inline SVG QR code for the authenticator app (no image files are written)."""
    image = qrcode.make(uri, image_factory=qrcode.image.svg.SvgPathImage, box_size=8)
    return image.to_string(encoding="unicode")


def _matching_step(secret, code):
    """Time step the code belongs to (allowing 30 seconds of clock difference), or None."""
    if not (len(code) == 6 and code.isascii() and code.isdigit()):
        return None
    totp = pyotp.TOTP(secret)
    now = timezone.now()
    for offset in (0, -1, 1):
        moment = now + timedelta(seconds=offset * totp.interval)
        if secrets.compare_digest(totp.at(moment), code):
            return totp.timecode(moment)
    return None


def code_matches_secret(secret, code):
    return _matching_step(secret, code) is not None


# --- Backup codes -------------------------------------------------------------------------


def _normalize(code):
    return "".join(code.split()).replace("-", "").lower()


def generate_backup_codes(user):
    """Replace the user's backup codes with 10 new ones; return them in readable form once."""
    rng = secrets.SystemRandom()
    codes = ["".join(rng.choice(_BACKUP_ALPHABET) for _ in range(8)) for _ in range(BACKUP_CODE_COUNT)]
    with transaction.atomic():
        user.otp_backup_codes.all().delete()
        OTPBackupCode.objects.bulk_create(OTPBackupCode(user=user, code_hash=make_password(c)) for c in codes)
    return [f"{c[:4]}-{c[4:]}" for c in codes]


def remaining_backup_codes(user):
    return user.otp_backup_codes.filter(used_at__isnull=True).count()


# --- Email codes --------------------------------------------------------------------------


def masked_email(email):
    name, _, domain = email.partition("@")
    return f"{name[:1]}***@{domain}" if domain else "***"


def send_email_code(user):
    """Email a 6-digit code (valid 10 minutes, single use; at most 3 per 15 minutes)."""
    with transaction.atomic():
        user = User.objects.select_for_update().get(pk=user.pk)
        if is_locked(user) or not user.is_active:
            raise AccountLocked
        if not user.otp_confirmed or not user.email:
            raise NoEmailAddress
        now = timezone.now()
        limited = (
            user.otp_email_codes.filter(created_at__gte=now - EMAIL_CODE_WINDOW).count() >= EMAIL_CODE_LIMIT
        )
        if limited:
            audit.record("otp.email_refused", actor=user, target_type="User", target_id=user.pk)
        else:
            code = f"{secrets.randbelow(1_000_000):06d}"
            entry = OTPEmailCode.objects.create(
                user=user, code_hash=make_password(code), expires_at=now + EMAIL_CODE_LIFETIME
            )
    if limited:
        raise TooManyEmailCodes
    # Reserve the request under the user lock, then release it before network I/O.
    # Failed deliveries still count toward the limit and cannot be used to log in.
    try:
        sent = send_mail(
            subject="Your Student Attendance login code",
            message=(
                f"Your login code is {code}. It expires in 10 minutes and works once.\n\n"
                "If you did not try to log in, contact the Admin."
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
        )
        if not sent:
            raise EmailDeliveryFailed
    except (SMTPException, OSError, EmailDeliveryFailed):
        OTPEmailCode.objects.filter(pk=entry.pk).update(used_at=timezone.now())
        audit.record("otp.email_failed", actor=user, target_type="User", target_id=user.pk)
        raise EmailDeliveryFailed from None
    audit.record("otp.email_sent", actor=user, target_type="User", target_id=user.pk)
    return masked_email(user.email)


# --- Verification -------------------------------------------------------------------------


def _use_authenticator(user, code):
    if not (user.otp_confirmed and user.otp_secret and code.isdigit() and len(code) == 6):
        return False
    step = _matching_step(user.otp_secret, code)
    if step is None or (user.otp_last_step is not None and step <= user.otp_last_step):
        return False  # wrong, or already used (a code cannot be replayed)
    user.otp_last_step = step
    return True


def _use_email_code(user, code):
    if not (code.isdigit() and len(code) == 6):
        return False
    for entry in user.otp_email_codes.filter(used_at__isnull=True, expires_at__gt=timezone.now()):
        if check_password(code, entry.code_hash):
            entry.used_at = timezone.now()
            entry.save(update_fields=["used_at"])
            return True
    return False


def _use_backup_code(user, code):
    code = _normalize(code)
    if len(code) != 8:
        return False
    for entry in user.otp_backup_codes.filter(used_at__isnull=True):
        if check_password(code, entry.code_hash):
            entry.used_at = timezone.now()
            entry.save(update_fields=["used_at"])
            return True
    return False


def verify_code(user, code):
    """Check a login code. Returns (ok, locked).

    Accepts an authenticator code, an emailed code or a backup code. 5 consecutive wrong
    codes lock the account for 15 minutes (SEC-32). Every attempt is logged.
    """
    code = (code or "").strip()
    with transaction.atomic():
        user = User.objects.select_for_update().get(pk=user.pk)
        if is_locked(user) or not user.is_active:
            return False, True
        method = None
        if _use_authenticator(user, code):
            method = "authenticator"
        elif _use_email_code(user, code):
            method = "email"
        elif _use_backup_code(user, code):
            method = "backup"

        if method:
            user.otp_failed_count = 0
            user.save(update_fields=["otp_failed_count", "otp_last_step"])
            audit.record(
                "otp.success", actor=user, target_type="User", target_id=user.pk, new_value={"method": method}
            )
            return True, False

        return False, _record_failure(user, "otp.failure")


def _record_failure(user, action):
    """Caller holds the user row lock; setup and login share the same attempt limit."""
    user.otp_failed_count += 1
    locked = user.otp_failed_count >= MAX_FAILED_CODES
    if locked:
        user.otp_failed_count = 0
        user.locked_until = timezone.now() + LOCKOUT_DURATION
    user.save(update_fields=["otp_failed_count", "locked_until"])
    audit.record(action, actor=user, target_type="User", target_id=user.pk)
    if locked:
        audit.record("otp.lockout", actor=user, target_type="User", target_id=user.pk)
    return locked


def is_locked(user):
    return bool(user.locked_until and user.locked_until > timezone.now())


# --- Setup and reset ----------------------------------------------------------------------


def confirm_setup(user, secret, code):
    """Finish authenticator setup if the code matches; returns the new backup codes, or None."""
    with transaction.atomic():
        user = User.objects.select_for_update().get(pk=user.pk)
        if is_locked(user) or not user.is_active:
            raise AccountLocked
        if user.otp_confirmed:
            raise AlreadyConfigured
        step = _matching_step(secret, (code or "").strip())
        if step is None:
            _record_failure(user, "otp.setup_failure")
            return None
        user.otp_secret = secret
        user.otp_confirmed = True
        user.otp_last_step = step
        user.otp_failed_count = 0
        user.save(update_fields=["otp_secret", "otp_confirmed", "otp_last_step", "otp_failed_count"])
        codes = generate_backup_codes(user)
        audit.record("otp.setup", actor=user, target_type="User", target_id=user.pk)
    return codes


def reset_otp(*, user, reset_by):
    """Admin reset (SEC-31): the user must set up the authenticator app again at next login."""
    with transaction.atomic():
        user = User.objects.select_for_update().get(pk=user.pk)
        user.otp_secret = ""
        user.otp_confirmed = False
        user.otp_last_step = None
        user.otp_failed_count = 0
        user.otp_reset_token = uuid.uuid4()
        user.save(
            update_fields=[
                "otp_secret",
                "otp_confirmed",
                "otp_last_step",
                "otp_failed_count",
                "otp_reset_token",
            ]
        )
        user.otp_backup_codes.all().delete()
        user.otp_email_codes.all().delete()
        audit.record("otp.reset", actor=reset_by, target_type="User", target_id=user.pk)
