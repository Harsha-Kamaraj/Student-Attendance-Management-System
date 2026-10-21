"""Students (BL-07 / UC-02), sections and enrollment (BL-10 / UC-05), subjects (BL-09 / UC-04)."""

from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.db import IntegrityError, transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_POST

from apps.accounts.models import Role
from apps.accounts.permissions import (
    can_edit_subject,
    get_visible_or_deny,
    has_permission,
    requires,
    visible_students,
)
from apps.accounts.services import provision_account
from apps.attendance.models import AttendanceSession
from apps.audit import services as audit

from .forms import (
    EnrollmentForm,
    SectionForm,
    StudentCreateForm,
    StudentUpdateForm,
    SubjectForm,
    SubjectOfferForm,
)
from .models import Enrollment, Section, Student, Subject, TeachingAssignment


@never_cache
@requires("students.view")
def student_list(request):
    students = visible_students(request.user).select_related("user", "home_section").order_by("roll_number")
    return render(request, "academics/student_list.html", {"students": students})


@never_cache
@requires("students.view")
def student_detail(request, pk):
    student = get_visible_or_deny(
        visible_students(request.user).select_related("user", "home_section"), Student, pk
    )
    enrollments = student.enrollments.select_related("assignment__section", "assignment__subject")
    return render(request, "academics/student_detail.html", {"student": student, "enrollments": enrollments})


@never_cache
@requires("students.manage")
def student_create(request):
    form = StudentCreateForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        data = form.cleaned_data
        try:
            with transaction.atomic():
                account, password = provision_account(
                    username=data["roll_number"],
                    role=Role.STUDENT,
                    email=data["email"],
                    created_by=request.user,
                )
                student = Student.objects.create(
                    user=account,
                    roll_number=data["roll_number"],
                    full_name=data["full_name"],
                    home_section=data["home_section"],
                )
                audit.record(
                    "student.create",
                    actor=request.user,
                    target_type="Student",
                    target_id=student.pk,
                    new_value={"roll_number": student.roll_number, "section": str(student.home_section)},
                )
        except IntegrityError:
            form.add_error("roll_number", "This roll number already exists.")
        else:
            return render(
                request,
                "academics/student_created.html",
                {"student": student, "temporary_password": password},
            )
    return render(request, "academics/student_form.html", {"form": form, "creating": True})


@never_cache
@requires("students.manage")
def student_edit(request, pk):
    student = get_object_or_404(Student.objects.select_related("user", "home_section"), pk=pk)
    initial = {
        "full_name": student.full_name,
        "class_name": student.home_section.class_name if student.home_section else "",
        "home_section": student.home_section,
        "email": student.user.email,
    }
    form = StudentUpdateForm(request.POST or None, initial=initial)
    if request.method == "POST" and form.is_valid():
        data = form.cleaned_data
        previous = {"name": student.full_name, "section": str(student.home_section)}
        with transaction.atomic():
            student.full_name = data["full_name"]
            student.home_section = data["home_section"]
            student.save(update_fields=["full_name", "home_section"])
            student.user.email = data["email"]
            student.user.save(update_fields=["email"])
            audit.record(
                "student.update",
                actor=request.user,
                target_type="Student",
                target_id=student.pk,
                old_value=previous,
                new_value={"name": student.full_name, "section": str(student.home_section)},
            )
        messages.success(request, "Student details updated. Course enrollments are managed separately.")
        return redirect("student_detail", pk=pk)
    return render(
        request, "academics/student_form.html", {"form": form, "creating": False, "student": student}
    )


@never_cache
@requires("students.manage")
@require_POST
def student_deactivate(request, pk):
    student = get_object_or_404(Student.objects.select_related("user"), pk=pk)
    if student.user.is_active:
        with transaction.atomic():
            student.user.is_active = False
            student.user.save(update_fields=["is_active"])
            audit.record("student.deactivate", actor=request.user, target_type="Student", target_id=pk)
    messages.success(request, "Student deactivated. Historical attendance is retained.")
    return redirect("student_detail", pk=pk)


@never_cache
@requires("students.manage")
@require_POST
def student_reactivate(request, pk):
    student = get_object_or_404(Student.objects.select_related("user"), pk=pk)
    if not student.user.is_active:
        with transaction.atomic():
            student.user.is_active = True
            student.user.save(update_fields=["is_active"])
            audit.record("student.reactivate", actor=request.user, target_type="Student", target_id=pk)
    messages.success(request, "Student reactivated; previous missed sessions remain unchanged.")
    return redirect("student_detail", pk=pk)


@never_cache
@requires("students.manage")
def student_delete(request, pk):
    student = get_object_or_404(Student.objects.select_related("user", "home_section"), pk=pk)
    if request.method == "POST":
        reason = request.POST.get("reason", "").strip()
        if reason:
            with transaction.atomic():
                audit.record(
                    "student.delete",
                    actor=request.user,
                    target_type="Student",
                    target_id=pk,
                    old_value={"roll_number": student.roll_number, "name": student.full_name},
                    reason=reason,
                )
                # User.CASCADE removes the student profile, enrollment and attendance records.
                student.user.delete()
            messages.success(request, "Student account and associated records deleted.")
            return redirect("student_list")
        messages.error(request, "A deletion reason is required.")
    return render(
        request,
        "academics/student_confirm_delete.html",
        {
            "student": student,
            "enrollment_count": student.enrollments.count(),
            "attendance_count": student.attendance_records.count(),
        },
    )


@never_cache
@requires("sections.manage")
def section_list(request):
    sections = Section.objects.order_by("class_name", "name")
    return render(request, "academics/section_list.html", {"sections": sections})


@never_cache
@requires("sections.manage")
def section_create(request):
    form = SectionForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            with transaction.atomic():
                section = form.save()
                audit.record(
                    "section.create",
                    actor=request.user,
                    target_type="Section",
                    target_id=section.pk,
                    new_value={"class_name": section.class_name, "name": section.name},
                )
        except IntegrityError:
            form.add_error(None, "That section already exists in this class.")
        else:
            messages.success(request, "Class section created.")
            return redirect("section_detail", pk=section.pk)
    return render(request, "academics/section_form.html", {"form": form})


@never_cache
@requires("sections.manage")
def section_detail(request, pk):
    section = get_object_or_404(Section, pk=pk)
    assignments = TeachingAssignment.objects.filter(section=section).select_related("subject", "faculty")
    enrollments = (
        Enrollment.objects.filter(assignment__section=section)
        .select_related("student__user", "assignment__subject")
        .order_by("assignment__subject__code", "student__roll_number")
    )
    return render(
        request,
        "academics/section_detail.html",
        {"section": section, "assignments": assignments, "enrollments": enrollments},
    )


@never_cache
@requires("sections.manage")
def enrollment_create(request, pk):
    section = get_object_or_404(Section, pk=pk)
    form = EnrollmentForm(request.POST or None, section=section)
    if request.method == "POST" and form.is_valid():
        student = form.cleaned_data["student"]
        assignment = form.cleaned_data["assignment"]
        try:
            with transaction.atomic():
                enrollment = Enrollment.objects.create(student=student, assignment=assignment)
                audit.record(
                    "enrollment.create",
                    actor=request.user,
                    target_type="Enrollment",
                    target_id=enrollment.pk,
                    new_value={
                        "student": student.roll_number,
                        "subject": assignment.subject.code,
                        "section": str(section),
                    },
                )
        except IntegrityError:
            form.add_error(None, "A conflicting enrollment already exists. Reload the roster.")
        else:
            messages.success(request, "Student added to the subject roster.")
            return redirect("section_detail", pk=pk)
    return render(request, "academics/enrollment_form.html", {"section": section, "form": form})


@never_cache
@requires("sections.manage")
@require_POST
def enrollment_remove(request, pk, enrollment_pk):
    enrollment = get_object_or_404(
        Enrollment.objects.select_related("student", "assignment__subject"),
        pk=enrollment_pk,
        assignment__section_id=pk,
    )
    with transaction.atomic():
        audit.record(
            "enrollment.remove",
            actor=request.user,
            target_type="Enrollment",
            target_id=enrollment.pk,
            old_value={
                "student": enrollment.student.roll_number,
                "subject": enrollment.assignment.subject.code,
                "section_id": pk,
            },
        )
        enrollment.delete()
    messages.success(request, "Enrollment removed. Previously recorded attendance was not erased.")
    return redirect("section_detail", pk=pk)


# --- Subjects (BL-09 / UC-04) -------------------------------------------------------------
# Admin and Faculty may create and view subjects; Faculty edit only subjects they teach;
# only the Admin deletes subjects or offers them in sections (BL-05 matrix).


def _subject_usage(subject):
    """Students enrolled and attendance sessions recorded for this subject."""
    return {
        "enrollments": Enrollment.objects.filter(subject=subject).count(),
        "sessions": AttendanceSession.objects.filter(assignment__subject=subject).count(),
    }


@never_cache
@requires("subjects.create")
def subject_list(request):
    subjects = Subject.objects.order_by("code")
    editable = {s.pk for s in subjects if can_edit_subject(request.user, s)}
    return render(request, "academics/subject_list.html", {"subjects": subjects, "editable": editable})


@never_cache
@requires("subjects.create")
def subject_create(request):
    form = SubjectForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            with transaction.atomic():
                subject = form.save()
                audit.record(
                    "subject.create",
                    actor=request.user,
                    target_type="Subject",
                    target_id=subject.pk,
                    new_value={"code": subject.code, "name": subject.name},
                )
        except IntegrityError:
            form.add_error("code", "A subject with this code already exists.")
        else:
            messages.success(request, f"Subject {subject.code} created.")
            return redirect("subject_detail", pk=subject.pk)
    return render(request, "academics/subject_form.html", {"form": form, "creating": True})


@never_cache
@requires("subjects.create")
def subject_detail(request, pk):
    subject = get_object_or_404(Subject, pk=pk)
    assignments = (
        TeachingAssignment.objects.filter(subject=subject)
        .select_related("section", "faculty")
        .order_by("section__class_name", "section__name")
    )
    return render(
        request,
        "academics/subject_detail.html",
        {
            "subject": subject,
            "assignments": assignments,
            "can_edit": can_edit_subject(request.user, subject),
            "can_manage": has_permission(request.user, "sections.manage"),
            "usage": _subject_usage(subject),
        },
    )


@never_cache
@requires("subjects.edit")
def subject_edit(request, pk):
    subject = get_object_or_404(Subject, pk=pk)
    if not can_edit_subject(request.user, subject):
        raise PermissionDenied("subject not taught by this faculty member")
    previous_name = subject.name
    form = SubjectForm(request.POST or None, instance=subject)
    if request.method == "POST" and form.is_valid():
        with transaction.atomic():
            subject = form.save()
            audit.record(
                "subject.update",
                actor=request.user,
                target_type="Subject",
                target_id=subject.pk,
                old_value={"name": previous_name},
                new_value={"name": subject.name},
            )
        messages.success(request, "Subject updated.")
        return redirect("subject_detail", pk=pk)
    return render(
        request, "academics/subject_form.html", {"form": form, "creating": False, "subject": subject}
    )


@never_cache
@requires("subjects.delete")
def subject_delete(request, pk):
    subject = get_object_or_404(Subject, pk=pk)
    usage = _subject_usage(subject)
    blocked = usage["enrollments"] or usage["sessions"]
    if request.method == "POST" and not blocked:
        with transaction.atomic():
            audit.record(
                "subject.delete",
                actor=request.user,
                target_type="Subject",
                target_id=subject.pk,
                old_value={"code": subject.code, "name": subject.name},
            )
            subject.delete()
        messages.success(request, f"Subject {subject.code} deleted.")
        return redirect("subject_list")
    return render(
        request,
        "academics/subject_confirm_delete.html",
        {"subject": subject, "usage": usage, "blocked": blocked},
    )


@never_cache
@requires("sections.manage")
def subject_offer(request, pk):
    subject = get_object_or_404(Subject, pk=pk)
    form = SubjectOfferForm(request.POST or None, subject=subject)
    if request.method == "POST" and form.is_valid():
        section = form.cleaned_data["section"]
        try:
            with transaction.atomic():
                assignment = TeachingAssignment.objects.create(section=section, subject=subject)
                audit.record(
                    "subject.offer",
                    actor=request.user,
                    target_type="TeachingAssignment",
                    target_id=assignment.pk,
                    new_value={"subject": subject.code, "section": str(section)},
                )
        except IntegrityError:
            form.add_error("section", "This subject is already offered in that section.")
        else:
            messages.success(request, f"{subject.code} is now offered in {section}. Assign its faculty next.")
            return redirect("subject_detail", pk=pk)
    return render(request, "academics/subject_offer.html", {"subject": subject, "form": form})


@never_cache
@requires("sections.manage")
@require_POST
def subject_withdraw(request, pk, assignment_pk):
    assignment = get_object_or_404(
        TeachingAssignment.objects.select_related("section", "subject"), pk=assignment_pk, subject_id=pk
    )
    if assignment.enrollments.exists() or assignment.sessions.exists():
        messages.error(
            request,
            f"{assignment.subject.code} cannot be withdrawn from {assignment.section}: students are enrolled "
            "or attendance exists. Remove the enrollments first; recorded attendance is never deleted.",
        )
        return redirect("subject_detail", pk=pk)
    with transaction.atomic():
        audit.record(
            "subject.withdraw",
            actor=request.user,
            target_type="TeachingAssignment",
            target_id=assignment.pk,
            old_value={"subject": assignment.subject.code, "section": str(assignment.section)},
        )
        assignment.delete()
    messages.success(request, f"{assignment.subject.code} withdrawn from {assignment.section}.")
    return redirect("subject_detail", pk=pk)
