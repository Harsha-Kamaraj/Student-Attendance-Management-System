"""Select an authorized teaching assignment and a valid attendance session (BL-12)."""

from django import forms
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from apps.academics.forms import AssignmentChoiceField, limit_to_today
from apps.academics.models import Enrollment, Subject, TeachingAssignment
from apps.accounts.forms import BootstrapMixin
from apps.accounts.models import Role
from apps.accounts.permissions import visible_assignments

from .models import BREAKS_NOTE, PERIOD_CHOICES, AttendanceThreshold
from .services import OUTSIDE_WINDOW_MESSAGE, earliest_faculty_date


class AttendanceSelectionForm(BootstrapMixin, forms.Form):
    assignment = AssignmentChoiceField(
        queryset=TeachingAssignment.objects.none(), label="Subject and class", empty_label="Select a subject"
    )
    date = forms.DateField(widget=forms.DateInput(attrs={"type": "date"}), initial=timezone.localdate)
    period = forms.TypedChoiceField(coerce=int, choices=PERIOD_CHOICES, help_text=BREAKS_NOTE)

    def __init__(self, *args, user, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        self.fields["assignment"].queryset = (
            visible_assignments(user)
            .select_related("section", "subject")
            .order_by("subject__code", "section__class_name", "section__name")
        )
        limit_to_today(self.fields["date"])
        if user.role == Role.FACULTY:
            # Faculty may only record within the correction window, so earlier days are greyed out too.
            self.fields["date"].widget.attrs["min"] = earliest_faculty_date().isoformat()

    def clean_date(self):
        day = self.cleaned_data["date"]
        if day > timezone.localdate():
            raise ValidationError("Attendance cannot be recorded for a future date.")
        if self.user.role == Role.FACULTY and day < earliest_faculty_date():
            raise ValidationError(OUTSIDE_WINDOW_MESSAGE)
        return day


class AttendanceSummaryFilterForm(BootstrapMixin, forms.Form):
    """Optional subject and inclusive date filters for a student's own report (BL-15)."""

    subject = forms.ModelChoiceField(
        queryset=Subject.objects.none(),
        required=False,
        empty_label="All subjects",
    )
    start_date = forms.DateField(required=False, widget=forms.DateInput(attrs={"type": "date"}))
    end_date = forms.DateField(required=False, widget=forms.DateInput(attrs={"type": "date"}))

    def __init__(self, *args, student, **kwargs):
        super().__init__(*args, **kwargs)
        from .models import AttendanceRecord

        enrolled = Enrollment.objects.filter(student=student).values("subject_id")
        recorded = AttendanceRecord.objects.filter(student=student).values("session__assignment__subject_id")
        self.fields["subject"].queryset = Subject.objects.filter(
            models.Q(pk__in=enrolled) | models.Q(pk__in=recorded)
        ).order_by("code")
        limit_to_today(self.fields["start_date"], self.fields["end_date"])

    def clean(self):
        cleaned = super().clean()
        start = cleaned.get("start_date")
        end = cleaned.get("end_date")
        if start and end and start > end:
            raise ValidationError({"end_date": "End date must be on or after the start date."})
        return cleaned


class AttendanceThresholdForm(BootstrapMixin, forms.Form):
    value = forms.IntegerField(
        label="Minimum attendance percentage",
        min_value=1,
        max_value=100,
        initial=75,
        help_text="Enter a whole number from 1 to 100. The default is 75%.",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["value"].initial = AttendanceThreshold.current_value()
