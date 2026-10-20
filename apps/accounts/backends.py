from django.contrib.auth.backends import ModelBackend

from .models import User
from .services import check_login


class AccountBackend(ModelBackend):
    """Used by every login form, including the Django admin, so the lockout always applies."""

    def authenticate(self, request, username=None, password=None, **kwargs):
        username = username or kwargs.get(User.USERNAME_FIELD)
        if not username or not password:
            return None
        return check_login(request, username, password)
