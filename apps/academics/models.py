"""Students, faculty, subjects, sections, teaching assignments and enrolments."""

from django.conf import settings
from django.db import models


class Student(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="student_profile"
    )
    roll_number = models.CharField(max_length=20, unique=True)
    full_name = models.CharField(max_length=150)
    # Home class/section; per-subject electives remain controlled by Enrollment.
    # Nullable for student records created before BL-07.
    home_section = models.ForeignKey(
        "Section", on_delete=models.SET_NULL, null=True, blank=True, related_name="home_students"
    )

    def __str__(self):
        return f"{self.roll_number} – {self.full_name}"


class Faculty(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="faculty_profile"
    )
    faculty_id = models.CharField(max_length=20, unique=True)
    full_name = models.CharField(max_length=150)
    department = models.CharField(max_length=100)

    class Meta:
        verbose_name_plural = "faculty"

    def __str__(self):
        return f"{self.faculty_id} – {self.full_name}"


class Subject(models.Model):
    code = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=150)

    def __str__(self):
        return f"{self.code} – {self.name}"


class Section(models.Model):
    class_name = models.CharField(max_length=100, help_text="For example: B.Tech CSE Year 2")
    name = models.CharField(max_length=20, help_text="For example: A")

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["class_name", "name"], name="section_unique_name"),
        ]

    def __str__(self):
        return f"{self.class_name} {self.name}"


class TeachingAssignment(models.Model):
    """A subject taught in a section, and the faculty member who teaches it.

    A faculty member who still has assignments cannot be deleted (BL-01 D-04).
    """

    section = models.ForeignKey(Section, on_delete=models.CASCADE, related_name="assignments")
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name="assignments")
    faculty = models.ForeignKey(
        Faculty, on_delete=models.PROTECT, null=True, blank=True, related_name="assignments"
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["section", "subject"], name="assignment_unique_section_subject"),
        ]

    def __str__(self):
        return f"{self.subject.code} in {self.section}"


class Enrollment(models.Model):
    """A student taking one subject in one section.

    `subject` repeats `assignment.subject` so the database can enforce
    one section per subject per student (BL-01 D-19). It is filled in on save.
    """

    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name="enrollments")
    assignment = models.ForeignKey(TeachingAssignment, on_delete=models.CASCADE, related_name="enrollments")
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name="+", editable=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["student", "subject"], name="enrollment_one_section_per_subject"),
        ]

    def __str__(self):
        return f"{self.student} in {self.assignment}"

    def save(self, *args, **kwargs):
        self.subject_id = self.assignment.subject_id
        super().save(*args, **kwargs)
