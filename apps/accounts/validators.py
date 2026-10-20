from django.core.exceptions import ValidationError

SPECIAL_CHARACTERS = "!@#$%^&*()-_=+[]{};:,.?/"


class PasswordComplexityValidator:
    """SEC-04: upper case, lower case, a digit and a special character (length is checked separately)."""

    def validate(self, password, user=None):
        missing = []
        if not any(c.isupper() for c in password):
            missing.append("an upper-case letter")
        if not any(c.islower() for c in password):
            missing.append("a lower-case letter")
        if not any(c.isdigit() for c in password):
            missing.append("a digit")
        if not any(c in SPECIAL_CHARACTERS for c in password):
            missing.append("a special character")
        if missing:
            raise ValidationError(
                "Password must contain " + ", ".join(missing) + ".", code="password_too_simple"
            )

    def get_help_text(self):
        return (
            "Your password must contain an upper-case letter, a lower-case letter, "
            "a digit and a special character."
        )
