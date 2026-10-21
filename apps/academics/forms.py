"""Admin student creation and editing, including class/section validation (BL-07)."""

import re

from django import forms
from django.core.exceptions import ValidationError

from apps.accounts.forms import BootstrapMixin
from apps.accounts.models import User

from .models import Section, Student


class StudentFieldsForm(BootstrapMixin, forms.Form):
    full_name = forms.CharField(max_length=150, label="Full name")
    class_name = forms.ChoiceField(label="Class", choices=[])
    home_section = forms.ModelChoiceField(
        queryset=Section.objects.all(), label="Section", empty_label="Select a section"
    )
    email = forms.EmailField(label="Email")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        names = Section.objects.order_by("class_name").values_list("class_name", flat=True).distinct()
        self.fields["class_name"].choices = [("", "Select a class"), *((name, name) for name in names)]
        self.fields["home_section"].queryset = Section.objects.order_by("class_name", "name")

    def clean_full_name(self):
        value = self.cleaned_data["full_name"].strip()
        if not value:
            raise ValidationError("Student name is required.")
        return value

    def clean(self):
        cleaned = super().clean()
        section = cleaned.get("home_section")
        class_name = cleaned.get("class_name")
        if section is not None and class_name and section.class_name != class_name:
            self.add_error("home_section", "The section must belong to the selected class.")
        return cleaned


class StudentCreateForm(StudentFieldsForm):
    roll_number = forms.CharField(max_length=20, label="Roll number")

    def clean_roll_number(self):
        roll = User.normalize_username(self.cleaned_data["roll_number"])
        if not re.fullmatch(r"[A-Z0-9@.+_-]+", roll):
            raise ValidationError("Use letters, numbers or @ . + - _ only.")
        if (
            User.objects.filter(username=roll).exists()
            or Student.objects.filter(roll_number__iexact=roll).exists()
        ):
            raise ValidationError("This roll number already exists.")
        return roll


class StudentUpdateForm(StudentFieldsForm):
    """Roll numbers are intentionally immutable: they are also login identifiers."""
