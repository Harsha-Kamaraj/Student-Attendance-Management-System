"""Attendance corrections and the Admin's calendar-day policy (BL-17)."""

from django import forms

from apps.accounts.forms import BootstrapMixin
from apps.accounts.models import Role

from .models import Status


class AttendanceCorrectionForm(BootstrapMixin, forms.Form):
    status = forms.ChoiceField(choices=Status.choices, label="Corrected status")
    reason = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"rows": 3}),
        help_text="Describe the correction. A reason is required for every Admin override.",
    )

    def __init__(self, *args, user, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["reason"].required = user.role == Role.ADMIN


class CorrectionWindowForm(BootstrapMixin, forms.Form):
    days = forms.IntegerField(
        min_value=0,
        max_value=30,
        label="Faculty correction window (calendar days)",
        help_text="0 allows only the session date. The default is 2 days. All deadlines use IST.",
    )
    reason = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 3}),
        help_text="Required. This policy change and its reason are recorded in the audit log.",
    )
