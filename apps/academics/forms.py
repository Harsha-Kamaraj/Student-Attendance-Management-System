"""Admin student creation and editing, including class/section validation (BL-07)."""

import re

from django import forms
from django.core.exceptions import ValidationError

from apps.accounts.forms import BootstrapMixin
from apps.accounts.models import User

from .models import Enrollment, Faculty, Section, Student, Subject, TeachingAssignment


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


class SectionForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = Section
        fields = ["class_name", "name"]

    def clean_class_name(self):
        value = self.cleaned_data["class_name"].strip()
        if not value:
            raise ValidationError("Class is required.")
        return value

    def clean_name(self):
        value = self.cleaned_data["name"].strip().upper()
        if not value:
            raise ValidationError("Section is required.")
        return value

    def clean(self):
        cleaned = super().clean()
        class_name, name = cleaned.get("class_name"), cleaned.get("name")
        if (
            class_name
            and name
            and Section.objects.filter(class_name__iexact=class_name, name__iexact=name).exists()
        ):
            raise ValidationError("That section already exists in this class.")
        return cleaned


class EnrollmentForm(BootstrapMixin, forms.Form):
    student = forms.ModelChoiceField(queryset=Student.objects.none())
    assignment = forms.ModelChoiceField(queryset=TeachingAssignment.objects.none(), label="Subject")

    def __init__(self, *args, section, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["student"].queryset = Student.objects.filter(user__is_active=True).order_by("roll_number")
        self.fields["assignment"].queryset = (
            TeachingAssignment.objects.filter(section=section)
            .select_related("subject")
            .order_by("subject__code")
        )

    def clean(self):
        cleaned = super().clean()
        student, assignment = cleaned.get("student"), cleaned.get("assignment")
        if student and assignment:
            existing = (
                Enrollment.objects.filter(student=student, subject=assignment.subject)
                .select_related("assignment__section", "assignment__subject")
                .first()
            )
            if existing:
                raise ValidationError(
                    f"{student.roll_number} is already enrolled in {assignment.subject.code} "
                    f"in section {existing.assignment.section}. Remove that enrollment first."
                )
        return cleaned


class SubjectForm(BootstrapMixin, forms.ModelForm):
    """Create or rename a subject (BL-09). Codes are stored in capitals and cannot change later."""

    class Meta:
        model = Subject
        fields = ["code", "name"]
        labels = {"code": "Subject code", "name": "Subject name"}
        help_texts = {"code": "Letters, digits and hyphens, e.g. CS101. Cannot be changed later."}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            self.fields["code"].disabled = True
            self.fields["code"].help_text = "Subject codes cannot be changed."

    def clean_code(self):
        if self.instance.pk:
            return self.instance.code
        code = self.cleaned_data["code"].strip().upper()
        if not re.fullmatch(r"[A-Z0-9-]+", code):
            raise ValidationError("Use letters, digits and hyphens only.")
        if Subject.objects.filter(code__iexact=code).exists():
            raise ValidationError("A subject with this code already exists.")
        return code

    def clean_name(self):
        value = self.cleaned_data["name"].strip()
        if not value:
            raise ValidationError("Subject name is required.")
        return value


class SubjectOfferForm(BootstrapMixin, forms.Form):
    """Offer a subject in a section (creates its teaching assignment; faculty is chosen in BL-11)."""

    section = forms.ModelChoiceField(queryset=Section.objects.none(), empty_label="Select a section")

    def __init__(self, *args, subject, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["section"].queryset = Section.objects.exclude(assignments__subject=subject).order_by(
            "class_name", "name"
        )


class FacultyFieldsForm(BootstrapMixin, forms.Form):
    full_name = forms.CharField(max_length=150, label="Full name")
    department = forms.CharField(max_length=100)
    email = forms.EmailField(label="Email")

    def clean_full_name(self):
        value = self.cleaned_data["full_name"].strip()
        if not value:
            raise ValidationError("Faculty name is required.")
        return value

    def clean_department(self):
        value = self.cleaned_data["department"].strip()
        if not value:
            raise ValidationError("Department is required.")
        return value


class FacultyCreateForm(FacultyFieldsForm):
    faculty_id = forms.CharField(max_length=20, label="Faculty ID")
    field_order = ["faculty_id", "full_name", "department", "email"]

    def clean_faculty_id(self):
        code = User.normalize_username(self.cleaned_data["faculty_id"])
        if not re.fullmatch(r"[A-Z0-9@.+_-]+", code):
            raise ValidationError("Use letters, numbers or @ . + - _ only.")
        if (
            User.objects.filter(username=code).exists()
            or Faculty.objects.filter(faculty_id__iexact=code).exists()
        ):
            raise ValidationError("This faculty ID already exists.")
        return code


class FacultyUpdateForm(FacultyFieldsForm):
    """Faculty IDs are immutable: they are also login identifiers."""


def _active_faculty():
    """Only active faculty can be given classes (BL-11 decision)."""
    return Faculty.objects.filter(user__is_active=True).order_by("faculty_id")


class ClassAssignForm(BootstrapMixin, forms.Form):
    """Add a subject to a section together with its teacher (BL-11)."""

    subject = forms.ModelChoiceField(queryset=Subject.objects.none(), empty_label="Select a subject")
    faculty = forms.ModelChoiceField(
        queryset=Faculty.objects.none(), label="Teacher", empty_label="Select a teacher"
    )

    def __init__(self, *args, section, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["subject"].queryset = Subject.objects.exclude(assignments__section=section).order_by(
            "code"
        )
        self.fields["faculty"].queryset = _active_faculty()


class TeacherForm(BootstrapMixin, forms.Form):
    """Assign, change or remove the teacher of one class (BL-11)."""

    faculty = forms.ModelChoiceField(
        queryset=Faculty.objects.none(), label="Teacher", required=False, empty_label="Not assigned"
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["faculty"].queryset = _active_faculty()
