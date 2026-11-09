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
    class_name = models.CharField(
        max_length=100, verbose_name="Dept and sem", help_text="For example: B.Tech in CS 5th sem"
    )
    name = models.CharField(max_length=20, verbose_name="Section", help_text="For example: K")
    year = models.PositiveSmallIntegerField(
        null=True, blank=True, verbose_name="Year", help_text="Batch year, for example: 2028. Optional."
    )

    class Meta:
        constraints = [
            # A blank year counts as one value, so "CS 5th sem K" without a year stays unique.
            models.UniqueConstraint(
                fields=["class_name", "name", "year"], name="section_unique_name", nulls_distinct=False
            ),
        ]

    def __str__(self):
        label = f"{self.class_name} {self.name}"
        return f"{label} ({self.year})" if self.year else label


class TeachingAssignment(models.Model):
    """A subject taught in a section, and the faculty member who teaches it.

    A faculty member who still has assignments cannot be deleted (BL-01 D-04).
    """

    section = models.ForeignKey(Section, on_delete=models.CASCADE, related_name="assignments")
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name="assignments")
    faculty = models.ForeignKey(
        Faculty, on_delete=models.PROTECT, null=True, blank=True, related_name="assignments"
    )
    # Set by the Admin on the Semester classes page; lets students see how many of the
    # remaining classes they must attend to finish the semester at the threshold.
    planned_sessions = models.PositiveSmallIntegerField(
        null=True, blank=True, verbose_name="Classes planned this semester"
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["section", "subject"], name="assignment_unique_section_subject"),
            models.CheckConstraint(
                condition=models.Q(planned_sessions__isnull=True)
                | models.Q(planned_sessions__range=(1, 500)),
                name="assignment_planned_sessions_range",
            ),
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


class Weekday(models.IntegerChoices):
    MONDAY = 0, "Monday"
    TUESDAY = 1, "Tuesday"
    WEDNESDAY = 2, "Wednesday"
    THURSDAY = 3, "Thursday"
    FRIDAY = 4, "Friday"
    SATURDAY = 5, "Saturday"


class TimetableSlot(models.Model):
    """A weekly class: this subject offering meets on this weekday in this period.

    The Admin keeps the timetable. Faculty dashboards use it to remind teachers of
    today's classes and which of them still need attendance marked.
    """

    assignment = models.ForeignKey(
        TeachingAssignment, on_delete=models.CASCADE, related_name="timetable_slots"
    )
    weekday = models.PositiveSmallIntegerField(choices=Weekday.choices)
    period = models.PositiveSmallIntegerField()

    class Meta:
        ordering = ["weekday", "period"]
        constraints = [
            models.UniqueConstraint(fields=["assignment", "weekday", "period"], name="timetable_slot_unique"),
            models.CheckConstraint(condition=models.Q(period__range=(1, 6)), name="timetable_period_range"),
            models.CheckConstraint(condition=models.Q(weekday__range=(0, 5)), name="timetable_weekday_range"),
        ]

    def __str__(self):
        return f"{self.assignment} on {self.get_weekday_display()} period {self.period}"
