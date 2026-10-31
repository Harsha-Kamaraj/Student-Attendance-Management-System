"""Account provisioning, password resets and login checks (BL-04)."""

import logging
import secrets
from datetime import timedelta

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.mail import send_mail
from django.db import transaction
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.debug import sensitive_variables

from apps.audit import services as audit

from .credentials import require_account_admin
from .models import Role, User

MAX_FAILED_LOGINS = 5  # SEC-03
LOCKOUT_DURATION = timedelta(minutes=15)  # SEC-03
RESET_REQUEST_INTERVAL = timedelta(minutes=15)

logger = logging.getLogger(__name__)
TEMPORARY_PASSWORD_LENGTH = 12

# Characters that are easy to tell apart when read aloud or copied by hand.
_UPPER = "ABCDEFGHJKLMNPQRSTUVWXYZ"
_LOWER = "abcdefghijkmnpqrstuvwxyz"
_DIGITS = "23456789"
_SPECIAL = "!@#$%&*-_?"


def generate_temporary_password():
    """A random password that always satisfies the SEC-04 password policy."""
    rng = secrets.SystemRandom()
    chars = [rng.choice(group) for group in (_UPPER, _LOWER, _DIGITS, _SPECIAL)]
    everything = _UPPER + _LOWER + _DIGITS + _SPECIAL
    chars += [rng.choice(everything) for _ in range(TEMPORARY_PASSWORD_LENGTH - len(chars))]
    rng.shuffle(chars)
    return "".join(chars)


@sensitive_variables()
def provision_account(*, username, role, email, created_by):
    """Create an account with a one-time temporary password (BL-01 D-02, SEC-06).

    Returns (user, temporary_password). The password is not stored in readable form.
    """
    require_account_admin(created_by)
    temporary_password = generate_temporary_password()
    with transaction.atomic():
        user = User.objects.create_user(
            username=username,
            email=email,
            password=temporary_password,
            role=role,
            must_change_password=True,
        )
        audit.record(
            "account.create",
            actor=created_by,
            target_type="User",
            target_id=user.pk,
            new_value={"username": user.username, "role": user.role},
        )
    return user, temporary_password


@sensitive_variables()
def reset_password(*, user, reset_by, temporary_only=False):
    """Admin reset: new temporary password, forced change at next login, lockout cleared."""
    require_account_admin(reset_by)
    temporary_password = generate_temporary_password()
    with transaction.atomic():
        user = User.objects.select_for_update().get(pk=user.pk)
        if temporary_only and (not user.must_change_password or not user.is_active):
            raise ValidationError(
                "Login details can only be resent for an active temporary-password account."
            )
        user.set_password(temporary_password)
        user.must_change_password = True
        user.failed_login_count = 0
        user.locked_until = None
        user.password_reset_requested_at = None
        user.save(
            update_fields=[
                "password",
                "must_change_password",
                "failed_login_count",
                "locked_until",
                "password_reset_requested_at",
            ]
        )
        audit.record("password.reset", actor=reset_by, target_type="User", target_id=user.pk)
    return temporary_password


def check_login(request, username, password):
    """Return the user if the credentials may log in, otherwise None.

    Applies the lockout (SEC-03) and logs every attempt (SEC-22). When the password
    is correct but the account is deactivated, `request.login_failure_reason` is set
    to "deactivated" so the login page can say so (UC-01 3b).
    """
    username = User.normalize_username(username)
    try:
        user = User.objects.get(username=username)
    except User.DoesNotExist:
        User().set_password(password)  # spend the same hashing time as a real check
        audit.record("login.failure", actor_username=username, target_type="User")
        return None

    now = timezone.now()
    with transaction.atomic():
        user = User.objects.select_for_update().get(pk=user.pk)

        if user.locked_until and user.locked_until > now:
            audit.record("login.locked", actor=user, target_type="User", target_id=user.pk)
            return None

        if not user.check_password(password):
            user.failed_login_count += 1
            action = "login.failure"
            if user.failed_login_count >= MAX_FAILED_LOGINS:
                user.locked_until = now + LOCKOUT_DURATION
                user.failed_login_count = 0
                action = "login.lockout"
            user.save(update_fields=["failed_login_count", "locked_until"])
            audit.record(action, actor=user, target_type="User", target_id=user.pk)
            return None

        if not user.is_active:
            if request is not None:
                request.login_failure_reason = "deactivated"
            audit.record("login.deactivated", actor=user, target_type="User", target_id=user.pk)
            return None

        if user.failed_login_count or user.locked_until:
            user.failed_login_count = 0
            user.locked_until = None
            user.save(update_fields=["failed_login_count", "locked_until"])
        audit.record("login.success", actor=user, target_type="User", target_id=user.pk)
        return user


def request_password_reset(username):
    """Record a forgotten-password request for the Admins; there is no self-service reset (BL-01).

    Returns the account to tell the Admins about, or None when nothing should be sent: unknown
    or deactivated usernames, or a repeat request within 15 minutes. The caller always shows the
    same reply, so the response never reveals whether an account exists (SEC-02).
    """
    username = User.normalize_username(username)
    now = timezone.now()
    with transaction.atomic():
        user = User.objects.select_for_update().filter(username=username, is_active=True).first()
        audit.record(
            "password.reset_requested",
            actor_username=username,
            target_type="User",
            target_id=user.pk if user else "",
        )
        if user is None:
            return None
        recent = user.password_reset_requested_at
        if recent and now - recent < RESET_REQUEST_INTERVAL:
            return None
        user.password_reset_requested_at = now
        user.save(update_fields=["password_reset_requested_at"])
    return user


def email_admins_about_reset_request(user):
    """Email every other active Admin. Delivery failures are logged, never shown to the requester."""
    admins = User.objects.filter(role=Role.ADMIN, is_active=True).exclude(pk=user.pk).exclude(email="")
    link = f"{settings.SITE_URL.rstrip('/')}{reverse('account_list')}"
    body = (
        f"{user.username} ({user.get_role_display()}) has asked for a password reset.\n\n"
        f"Open Accounts and choose Reset password next to {user.username}:\n{link}\n\n"
        "A new temporary password is emailed to them automatically. "
        "If you did not expect this request, you can ignore it."
    )
    sent = 0
    for admin in admins:
        try:
            send_mail(
                f"Password reset requested: {user.username}", body, settings.DEFAULT_FROM_EMAIL, [admin.email]
            )
        except Exception as exc:  # one failed delivery must not stop the others
            logger.warning("Reset-request email to admin %s failed: %s", admin.pk, exc.__class__.__name__)
            audit.record(
                "password.reset_request_email_failed",
                target_type="User",
                target_id=admin.pk,
                new_value={"error": exc.__class__.__name__},
            )
        else:
            sent += 1
    return sent
