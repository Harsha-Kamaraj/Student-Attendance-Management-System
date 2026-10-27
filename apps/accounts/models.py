import uuid

from django.contrib.auth.models import AbstractUser, UserManager
from django.db import models
from django.db.models.functions import Upper
from django.utils.crypto import salted_hmac


class Role(models.TextChoices):
    ADMIN = "ADMIN", "Admin"
    FACULTY = "FACULTY", "Faculty"
    STUDENT = "STUDENT", "Student"


class AccountManager(UserManager):
    def create_superuser(self, username, email=None, password=None, **extra_fields):
        extra_fields.setdefault("role", Role.ADMIN)
        return super().create_superuser(username, email, password, **extra_fields)


class User(AbstractUser):
    """Login account. Username is the roll number (students) or faculty ID (faculty) — BL-01 D-02.

    Usernames are stored in capitals so that login ignores case.
    """

    Role = Role

    role = models.CharField(max_length=10, choices=Role.choices)
    must_change_password = models.BooleanField(
        default=False, help_text="Set for Admin-created accounts with a temporary password (SEC-06)."
    )
    failed_login_count = models.PositiveSmallIntegerField(default=0)
    locked_until = models.DateTimeField(
        null=True, blank=True, help_text="Login blocked until this time (SEC-03, SEC-32)."
    )
    # Two-factor login (BL-33, SEC-29 to SEC-32)
    otp_secret = models.CharField(
        max_length=64, blank=True, help_text="Authenticator app secret. Never shown after setup."
    )
    otp_confirmed = models.BooleanField(default=False, help_text="True once the authenticator app is set up.")
    otp_failed_count = models.PositiveSmallIntegerField(
        default=0,
        help_text="Consecutive wrong one-time codes; kept separate so a password login cannot reset it.",
    )
    otp_last_step = models.BigIntegerField(
        null=True, blank=True, help_text="Last accepted authenticator time step, so a code cannot be reused."
    )
    otp_reset_token = models.UUIDField(default=uuid.uuid4, editable=False)

    objects = AccountManager()

    class Meta(AbstractUser.Meta):
        constraints = [
            models.CheckConstraint(condition=models.Q(role__in=Role.values), name="user_role_valid"),
            models.CheckConstraint(
                condition=models.Q(username=Upper("username")), name="user_username_uppercase"
            ),
        ]

    @classmethod
    def normalize_username(cls, username):
        return super().normalize_username(username).strip().upper()

    def _get_session_auth_hash(self, secret=None):
        """An OTP reset invalidates both pending and fully verified sessions, like a password reset."""
        return salted_hmac(
            "accounts.User.get_session_auth_hash",
            f"{self.password}:{self.otp_reset_token}",
            secret=secret,
            algorithm="sha256",
        ).hexdigest()


class OTPBackupCode(models.Model):
    """One of a user's 10 single-use backup codes, stored only as a hash (SEC-31)."""

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="otp_backup_codes")
    code_hash = models.CharField(max_length=128)
    used_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Backup code for {self.user} ({'used' if self.used_at else 'unused'})"


class OTPEmailCode(models.Model):
    """A one-time code sent by email: valid 10 minutes, single use, stored as a hash (SEC-32)."""

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="otp_email_codes")
    code_hash = models.CharField(max_length=128)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Email code for {self.user} ({'used' if self.used_at else 'unused'})"
