"""Select an authorized teaching assignment and a valid attendance session (BL-12)."""

from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone

from apps.academics.models import TeachingAssignment
from apps.accounts.forms import BootstrapMixin
from apps.accounts.permissions import visible_assignments

from .models import MAX_PERIODS_PER_DAY


class AttendanceSelectionForm(BootstrapMixin, forms.Form):
    assignment = forms.ModelChoiceField(
        queryset=TeachingAssignment.objects.none(), label="Class and subject", empty_label="Select a class"
    )
    date = forms.DateField(widget=forms.DateInput(attrs={"type": "date"}), initial=timezone.localdate)
    period = forms.TypedChoiceField(
        coerce=int, choices=[(i, f"Period {i}") for i in range(1, MAX_PERIODS_PER_DAY + 1)]
    )

    def __init__(self, *args, user, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["assignment"].queryset = (
            visible_assignments(user)
            .select_related("section", "subject")
            .order_by("section__class_name", "section__name", "subject__code")
        )

    def clean_date(self):
        day = self.cleaned_data["date"]
        if day > timezone.localdate():
            raise ValidationError("Attendance cannot be recorded for a future date.")
        return day
