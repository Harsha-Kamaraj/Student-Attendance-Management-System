from django.contrib.auth.models import AbstractUser, UserManager
from django.db import models
from django.db.models.functions import Upper


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
        null=True, blank=True, help_text="Login blocked until this time (SEC-03)."
    )

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
