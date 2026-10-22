from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth import views as auth_views
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_POST

from apps.academics.models import Enrollment, Faculty, Section, Student, TeachingAssignment
from apps.attendance.calculations import attendance_shortage_statistics, student_attendance_summary
from apps.attendance.models import AttendanceSession, AttendanceThreshold
from apps.audit import services as audit

from .decorators import role_required
from .forms import AccountCreateForm, ChangePasswordForm, LoginForm
from .models import Role, User
from .permissions import requires
from .services import provision_account, reset_password


class LoginView(auth_views.LoginView):
    template_name = "accounts/login.html"
    authentication_form = LoginForm
    redirect_authenticated_user = True


class PasswordChangeView(auth_views.PasswordChangeView):
    template_name = "accounts/password_change.html"
    form_class = ChangePasswordForm
    success_url = reverse_lazy("dashboard")

    def form_valid(self, form):
        response = super().form_valid(form)
        user = self.request.user
        user.must_change_password = False
        user.save(update_fields=["must_change_password"])
        audit.record("password.change", actor=user, target_type="User", target_id=user.pk)
        messages.success(self.request, "Your password has been changed.")
        return response


@never_cache
@require_POST
@login_required
def logout_view(request):
    """Invalidate the current session on a CSRF-protected POST (BL-06 / UC-12)."""
    user = request.user
    logout(request)  # Django flushes the server-side session and session cookie.
    audit.record("logout", actor=user, target_type="User", target_id=user.pk)
    messages.success(request, "You have been logged out.")
    return redirect("login")


DASHBOARDS = {
    Role.ADMIN: "dashboard_admin",
    Role.FACULTY: "dashboard_faculty",
    Role.STUDENT: "dashboard_student",
}


@never_cache
@login_required
def dashboard(request):
    """Send each user to the dashboard for their role (UC-01 step 5)."""
    return redirect(DASHBOARDS[request.user.role])


@never_cache
@role_required(Role.ADMIN)
def dashboard_admin(request):
    stats = attendance_shortage_statistics()
    context = {
        "student_count": Student.objects.count(),
        "faculty_count": Faculty.objects.count(),
        "section_count": Section.objects.count(),
        "session_count": AttendanceSession.objects.count(),
        **stats,
    }
    return render(request, "dashboard/admin.html", context)


@never_cache
@role_required(Role.FACULTY)
def dashboard_faculty(request):
    assignments = TeachingAssignment.objects.filter(faculty__user=request.user)
    stats = attendance_shortage_statistics(assignments=assignments)
    context = {
        "class_count": assignments.values("section_id").distinct().count(),
        "subject_count": assignments.values("subject_id").distinct().count(),
        "student_count": (
            Enrollment.objects.filter(assignment__in=assignments).values("student_id").distinct().count()
        ),
        "session_count": AttendanceSession.objects.filter(assignment__in=assignments).count(),
        **stats,
    }
    return render(request, "dashboard/faculty.html", context)


@never_cache
@role_required(Role.STUDENT)
def dashboard_student(request):
    student = Student.objects.filter(user=request.user).first()
    summary = student_attendance_summary(student) if student else None
    threshold = AttendanceThreshold.current_value()
    context = {
        "summary": summary,
        "threshold": threshold,
        "subject_shortages": sum(1 for row in summary.subjects if row.is_below_threshold(threshold))
        if summary
        else 0,
        "overall_below_threshold": summary.overall.is_below_threshold(threshold) if summary else False,
    }
    return render(request, "dashboard/student.html", context)


@never_cache
@requires("accounts.manage")
def account_list(request):
    users = User.objects.order_by("role", "username")
    return render(request, "accounts/account_list.html", {"users": users})


@never_cache
@requires("accounts.manage")
def account_create(request):
    form = AccountCreateForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user, temporary_password = provision_account(
            username=form.cleaned_data["username"],
            role=Role.ADMIN,
            email=form.cleaned_data["email"],
            created_by=request.user,
        )
        # Shown once, never stored in readable form (SEC-05, SEC-06).
        return render(
            request,
            "accounts/temporary_password.html",
            {"account": user, "temporary_password": temporary_password, "created": True},
        )
    return render(request, "accounts/account_create.html", {"form": form})


@never_cache
@require_POST
@requires("accounts.manage")
def account_reset_password(request, pk):
    user = get_object_or_404(User, pk=pk)
    temporary_password = reset_password(user=user, reset_by=request.user)
    return render(
        request,
        "accounts/temporary_password.html",
        {"account": user, "temporary_password": temporary_password, "created": False},
    )
