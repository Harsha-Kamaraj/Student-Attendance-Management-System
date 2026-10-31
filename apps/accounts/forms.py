import time

from django import forms
from django.contrib.auth.forms import AuthenticationForm, PasswordChangeForm
from django.core.exceptions import ValidationError

from .models import User


class BootstrapMixin:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            css = "form-select" if isinstance(field.widget, forms.Select) else "form-control"
            field.widget.attrs.setdefault("class", css)


class LoginForm(BootstrapMixin, AuthenticationForm):
    error_messages = {
        "invalid_login": "Invalid username or password.",  # SEC-02: same message for every failure
        "inactive": "This account is deactivated. Contact the Admin.",  # UC-01 3b
        "too_many": (
            "Too many failed attempts. Login for this account may now be paused for 15 minutes. "
            "Wait and try again, or use Forgot password to ask the Admin for a reset."
        ),
    }
    # Counted per browser session, not per account, so the warning appears the same way whether
    # or not the username exists and never reveals which accounts are real (SEC-02, SEC-03).
    FAILURES_KEY = "login_failure_times"
    FAILURE_WINDOW_SECONDS = 15 * 60
    FAILURE_LIMIT = 5

    def clean(self):
        session = getattr(self.request, "session", None)
        try:
            cleaned = super().clean()
        except ValidationError:
            if getattr(self.request, "login_failure_reason", None) == "deactivated":
                raise ValidationError(self.error_messages["inactive"], code="inactive") from None
            if session is not None and self._record_failure(session) >= self.FAILURE_LIMIT:
                raise ValidationError(self.error_messages["too_many"], code="too_many") from None
            raise
        if session is not None:
            session.pop(self.FAILURES_KEY, None)
        return cleaned

    def _record_failure(self, session):
        now = time.time()
        recent = [t for t in session.get(self.FAILURES_KEY, []) if now - t < self.FAILURE_WINDOW_SECONDS]
        recent.append(now)
        session[self.FAILURES_KEY] = recent
        return len(recent)


class ForgotPasswordForm(BootstrapMixin, forms.Form):
    username = forms.CharField(
        max_length=150,
        label="Username",
        help_text="Your roll number (students) or faculty ID (faculty).",
        widget=forms.TextInput(attrs={"autocomplete": "username", "autofocus": True}),
    )


class AccountCreateForm(BootstrapMixin, forms.ModelForm):
    """Admin accounts only. Students and faculty are added with their profiles (BL-07, BL-08)."""

    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ["username", "email"]
        help_texts = {"username": "Letters, digits and @ . + - _ only. Stored in capitals."}

    def clean_username(self):
        username = User.normalize_username(self.cleaned_data["username"])
        if User.objects.filter(username=username).exists():
            raise ValidationError("An account with this username already exists.")
        return username


class ChangePasswordForm(BootstrapMixin, PasswordChangeForm):
    pass


class OTPCodeForm(BootstrapMixin, forms.Form):
    code = forms.CharField(
        label="Code",
        max_length=20,
        help_text="The 6-digit code from your authenticator app or email, or one of your backup codes.",
        widget=forms.TextInput(attrs={"autocomplete": "one-time-code", "autofocus": True}),
    )


class ReauthenticateForm(BootstrapMixin, forms.Form):
    password = forms.CharField(label="Your password", widget=forms.PasswordInput)

    def __init__(self, *args, user, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user

    def clean_password(self):
        from .services import check_login

        password = self.cleaned_data["password"]
        if check_login(None, self.user.username, password) is None:
            raise ValidationError("Incorrect password.")
        return password
