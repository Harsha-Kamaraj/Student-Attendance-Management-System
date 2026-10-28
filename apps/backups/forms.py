from django import forms
from django.conf import settings

from apps.accounts.forms import BootstrapMixin


class ScheduleForm(BootstrapMixin, forms.Form):
    enabled = forms.BooleanField(
        required=False,
        label="Enable daily backups",
        widget=forms.CheckboxInput(attrs={"class": "form-check-input"}),
    )
    time = forms.TimeField(
        required=False,
        label="Daily time (India Standard Time)",
        widget=forms.TimeInput(attrs={"type": "time"}, format="%H:%M"),
        input_formats=["%H:%M"],
    )

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("enabled") and not cleaned.get("time"):
            self.add_error("time", "Choose a daily backup time.")
        return cleaned


class RestoreForm(BootstrapMixin, forms.Form):
    password = forms.CharField(label="Your current password", widget=forms.PasswordInput)
    confirm = forms.BooleanField(
        label="I understand that current application data will be replaced.",
        widget=forms.CheckboxInput(attrs={"class": "form-check-input"}),
    )


class ImportForm(BootstrapMixin, forms.Form):
    backup_file = forms.FileField(label="Encrypted backup file (.sambak)")

    def clean_backup_file(self):
        upload = self.cleaned_data["backup_file"]
        if upload.size > settings.BACKUP_MAX_BYTES:
            raise forms.ValidationError("The file exceeds the configured backup size limit.")
        if not upload.size:
            raise forms.ValidationError("Choose a non-empty encrypted backup file.")
        return upload
