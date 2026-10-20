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
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ["username", "role", "email"]
        labels = {"username": "Username (roll number or faculty ID)"}
        help_texts = {"username": "Letters, digits and @ . + - _ only. Stored in capitals."}

    def clean_username(self):
        username = User.normalize_username(self.cleaned_data["username"])
        if User.objects.filter(username=username).exists():
            raise ValidationError("An account with this username already exists.")
        return username


class ChangePasswordForm(BootstrapMixin, PasswordChangeForm):
    pass
