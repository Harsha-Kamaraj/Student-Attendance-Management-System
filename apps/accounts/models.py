from django.contrib.auth.models import AbstractUser, UserManager
from django.db import models


class Role(models.TextChoices):
    ADMIN = "ADMIN", "Admin"
    FACULTY = "FACULTY", "Faculty"
    STUDENT = "STUDENT", "Student"


class AccountManager(UserManager):
    def create_superuser(self, username, email=None, password=None, **extra_fields):
        extra_fields.setdefault("role", Role.ADMIN)
        return super().create_superuser(username, email, password, **extra_fields)


class User(AbstractUser):
    """Login account. Username is the roll number (students) or faculty ID (faculty) — BL-01 D-02."""

    Role = Role

    role = models.CharField(max_length=10, choices=Role.choices)
    must_change_password = models.BooleanField(
        default=False, help_text="Set for Admin-created accounts with a temporary password (SEC-06)."
    )

    objects = AccountManager()

    class Meta(AbstractUser.Meta):
        constraints = [
            models.CheckConstraint(condition=models.Q(role__in=Role.values), name="user_role_valid"),
        ]
