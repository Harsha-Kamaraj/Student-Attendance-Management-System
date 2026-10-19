from django.contrib.auth.models import AbstractUser


class User(AbstractUser):
    """Project user model.

    Defined before the first migration so that roles and account fields
    (BL-03, BL-04) can be added later without rebuilding the database.
    """
