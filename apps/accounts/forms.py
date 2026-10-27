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
    }

    def clean(self):
        try:
            return super().clean()
        except ValidationError:
            if getattr(self.request, "login_failure_reason", None) == "deactivated":
                raise ValidationError(self.error_messages["inactive"], code="inactive") from None
            raise


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
