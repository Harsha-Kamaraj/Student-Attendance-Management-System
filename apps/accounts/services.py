"""Account provisioning, password resets and login checks (BL-04)."""

import secrets
from datetime import timedelta

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone
from django.views.decorators.debug import sensitive_variables

from apps.audit import services as audit

from .credentials import require_account_admin
from .models import User

MAX_FAILED_LOGINS = 5  # SEC-03
LOCKOUT_DURATION = timedelta(minutes=15)  # SEC-03
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
        user.save(update_fields=["password", "must_change_password", "failed_login_count", "locked_until"])
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
