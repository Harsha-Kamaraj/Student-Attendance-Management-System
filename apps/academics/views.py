"""Student profiles and lifecycle management (BL-07 / UC-02)."""

from django.contrib import messages
from django.db import IntegrityError, transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_POST

from apps.accounts.models import Role
from apps.accounts.permissions import get_visible_or_deny, requires, visible_students
from apps.accounts.services import provision_account
from apps.audit import services as audit

from .forms import StudentCreateForm, StudentUpdateForm
from .models import Student


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
