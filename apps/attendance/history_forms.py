"""Optional filters for authorized attendance history (BL-16)."""

from django import forms
from django.core.exceptions import ValidationError
from django.db.models import Q

from apps.academics.models import Student, TeachingAssignment
from apps.accounts.forms import BootstrapMixin
from apps.accounts.permissions import (
    visible_assignments,
    visible_attendance_records,
    visible_students,
)

from .models import MAX_PERIODS_PER_DAY, Status


class AttendanceHistoryFilterForm(BootstrapMixin, forms.Form):
    search = forms.CharField(
        required=False,
        max_length=100,
        strip=True,
        label="Search student",
        widget=forms.TextInput(
            attrs={
                "placeholder": "Enter student name or roll number",
                "autocomplete": "off",
            }
        ),
    )

    assignment = forms.ModelChoiceField(
        queryset=TeachingAssignment.objects.none(),
        label="Class / section and subject",
        required=False,
        empty_label="All assigned classes and subjects",
    )

    student = forms.ModelChoiceField(
        queryset=Student.objects.none(),
        required=False,
        empty_label="All students",
    )

    start_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={"type": "date"}),
    )

    end_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={"type": "date"}),
    )

    period = forms.TypedChoiceField(
        required=False,
        coerce=int,
        empty_value=None,
        choices=[
            ("", "All periods"),
            *((number, number) for number in range(1, MAX_PERIODS_PER_DAY + 1)),
        ],
    )

    status = forms.ChoiceField(
        required=False,
        choices=[("", "All statuses"), *Status.choices],
    )

    def __init__(self, *args, user, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["assignment"].queryset = (
            visible_assignments(user)
            .select_related("section", "subject")
            .order_by(
                "section__class_name",
                "section__name",
                "subject__code",
            )
        )

        # Keep students with historical attendance available even if
        # their previous enrollment has been removed.
        recorded = visible_attendance_records(user).values("student_id")

        self.fields["student"].queryset = Student.objects.filter(
            Q(pk__in=recorded) | Q(pk__in=visible_students(user).values("pk"))
        ).order_by("roll_number")

    def clean(self):
        cleaned = super().clean()

        start = cleaned.get("start_date")
        end = cleaned.get("end_date")

        if start and end and start > end:
            raise ValidationError({"end_date": ("End date must be on or after the start date.")})

        return cleaned
