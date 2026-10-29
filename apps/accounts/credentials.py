"""BL-34: deliver temporary credentials after the account/profile transaction commits."""

from dataclasses import dataclass
from urllib.parse import urlsplit

from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.core.mail import EmailMessage
from django.core.validators import validate_email
from django.db import transaction
from django.urls import reverse
from django.views.decorators.debug import sensitive_variables

from apps.audit import services as audit

from .models import Role, User


@dataclass(frozen=True)
class CredentialDelivery:
    status: str
    address: str


def require_account_admin(actor):
    if not User.objects.filter(pk=getattr(actor, "pk", None), role=Role.ADMIN, is_active=True).exists():
        raise PermissionDenied("Only an active Admin can issue login details.")


def masked_address(address):
    local, separator, domain = address.partition("@")
    return f"{local[:1]}***@{domain}" if separator else "the account email address"


def login_link():
    # Do not trust the request Host header for links containing account instructions.
    base = settings.SITE_URL.rstrip("/")
    parsed = urlsplit(base)
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.hostname
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
        or (not settings.DEBUG and parsed.scheme != "https")
        or any(char.isspace() for char in base)
    ):
        raise ValueError("Configure SITE_URL with the application's public HTTPS address.")
    return base + reverse("login")


@sensitive_variables()
def deliver_login_details(*, user, temporary_password, actor, purpose):
    """Call only after successful creation/reset. Never persist or log the message/password.

    The short row lock serializes delivery with password resets and address edits. A stale
    password is not emailed. Transport failures return a safe result for the one-time fallback.
    SMTP runs synchronously so the Admin knows the result before leaving the page.
    """
    require_account_admin(actor)
    if purpose not in {"created", "reset", "resend"}:
        raise ValueError("Unknown credential delivery purpose")
    with transaction.atomic():
        current = User.objects.select_for_update().get(pk=user.pk)
        address = masked_address(current.email)
        details = {"purpose": purpose, "recipient": address}
        audit.record(
            "credentials.email_attempt",
            actor=actor,
            target_type="User",
            target_id=current.pk,
            new_value=details,
        )
        if not current.must_change_password or not current.check_password(temporary_password):
            status = "superseded"
        else:
            try:
                if not current.is_active:
                    raise ValueError("Inactive recipient")
                validate_email(current.email)
                link = login_link()
                backend = settings.EMAIL_BACKEND
                preview = backend == "django.core.mail.backends.console.EmailBackend"
                if (preview and not settings.DEBUG) or backend in {
                    "django.core.mail.backends.filebased.EmailBackend",
                    "django.core.mail.backends.dummy.EmailBackend",
                }:
                    raise ValueError("Unsupported credential email backend")
                message = EmailMessage(
                    subject="Your Student Attendance login details",
                    body=(
                        f"Username: {current.username}\n"
                        f"Temporary password: {temporary_password}\n"
                        f"Login: {link}\n\n"
                        "This password is temporary. You must change it at first login before using "
                        "the application. Complete the two-factor login steps when prompted.\n"
                        "If login details were reissued, only the latest password works.\n"
                        "Keep these details private."
                    ),
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    to=[current.email],
                )
                if message.send(fail_silently=False) != 1:
                    raise ValueError("Email was not accepted")
                status = "preview" if preview else "sent"
            except Exception:
                # Provider exceptions can contain the entire message or SMTP credentials.
                # Do not log their text or include it in an Admin response/debug report.
                status = "failed"
        action = (
            "credentials.email_sent"
            if status == "sent"
            else ("credentials.email_preview" if status == "preview" else "credentials.email_failed")
        )
        audit.record(
            action,
            actor=actor,
            target_type="User",
            target_id=current.pk,
            new_value={**details, "outcome": status},
        )
        return CredentialDelivery(status=status, address=address)


@sensitive_variables()
def delivery_context(*, user, temporary_password, actor, purpose):
    result = deliver_login_details(
        user=user, temporary_password=temporary_password, actor=actor, purpose=purpose
    )
    return {
        "delivery": result,
        "temporary_password": temporary_password if result.status == "failed" else "",
    }
