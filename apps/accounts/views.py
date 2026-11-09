from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth import views as auth_views
from django.contrib.auth.decorators import login_not_required, login_required
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Count, F
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.views.decorators.cache import never_cache
from django.views.decorators.debug import sensitive_variables
from django.views.decorators.http import require_POST

from apps.academics.models import Enrollment, Faculty, Section, Student, TeachingAssignment
from apps.attendance.calculations import (
    attendance_shortage_statistics,
    student_attendance_summary,
    subject_outlooks,
)
from apps.attendance.models import AttendanceSession, AttendanceThreshold
from apps.attendance.schedule import today_overview
from apps.audit import services as audit

from .credentials import delivery_context, masked_address
from .decorators import role_required
from .forms import AccountCreateForm, ChangePasswordForm, ForgotPasswordForm, LoginForm, SendCredentialsForm
from .models import Role, User
from .permissions import requires
from .services import (
    email_admins_about_reset_request,
    provision_account,
    request_password_reset,
    reset_password,
)


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
        user.password_reset_requested_at = None
        user.save(update_fields=["must_change_password", "password_reset_requested_at"])
        audit.record("password.change", actor=user, target_type="User", target_id=user.pk)
        messages.success(self.request, "Your password has been changed.")
        return response


@never_cache
@login_required
def my_profile(request):
    """The signed-in user's own details, read-only; only the Admin edits accounts (BL-01)."""
    user = request.user
    context = {"account": user}
    if user.role == Role.FACULTY:
        faculty = Faculty.objects.filter(user=user).first()
        context["faculty"] = faculty
        context["classes"] = (
            TeachingAssignment.objects.filter(faculty=faculty)
            .select_related("section", "subject")
            .annotate(student_count=Count("enrollments"))
            .order_by("subject__code", "section__class_name", "section__name")
            if faculty
            else []
        )
    elif user.role == Role.STUDENT:
        student = Student.objects.filter(user=user).select_related("home_section").first()
        context["student"] = student
        context["enrollments"] = (
            Enrollment.objects.filter(student=student)
            .select_related("assignment__section", "assignment__subject", "assignment__faculty")
            .order_by("subject__code")
            if student
            else []
        )
    return render(request, "accounts/profile.html", context)


# Per browser session, so one visitor cannot flood the Admins with requests for many usernames.
FORGOT_PASSWORD_SESSION_LIMIT = 5


@login_not_required
@never_cache
def forgot_password(request):
    """Ask the Admin to reset a forgotten password (BL-01: only the Admin resets passwords).

    Always shows the same confirmation, so the page never reveals whether a username exists.
    """
    if request.user.is_authenticated:
        return redirect("dashboard")
    form = ForgotPasswordForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        count = request.session.get("reset_requests", 0)
        request.session["reset_requests"] = count + 1
        if count < FORGOT_PASSWORD_SESSION_LIMIT:
            user = request_password_reset(form.cleaned_data["username"])
            if user is not None:
                email_admins_about_reset_request(user)
        return render(request, "accounts/forgot_password_sent.html")
    return render(request, "accounts/forgot_password.html", {"form": form})


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
        "reset_request_count": User.objects.filter(password_reset_requested_at__isnull=False).count(),
        **stats,
        **today_overview(TeachingAssignment.objects.all()),
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
        **today_overview(assignments),
    }
    return render(request, "dashboard/faculty.html", context)


@never_cache
@role_required(Role.STUDENT)
def dashboard_student(request):
    student = Student.objects.filter(user=request.user).first()
    summary = student_attendance_summary(student) if student else None
    threshold = AttendanceThreshold.current_value()
    subject_rows, overall_outlook = subject_outlooks(student, summary, threshold) if summary else ([], None)
    context = {
        "summary": summary,
        "threshold": threshold,
        "subject_rows": subject_rows,
        "overall_outlook": overall_outlook,
        "subject_shortages": sum(1 for row in summary.subjects if row.is_below_threshold(threshold))
        if summary
        else 0,
        "overall_below_threshold": summary.overall.is_below_threshold(threshold) if summary else False,
    }
    return render(request, "dashboard/student.html", context)


@never_cache
@requires("accounts.manage")
def account_list(request):
    # Pending reset requests first, so the Admin sees them straight away.
    users = User.objects.order_by(F("password_reset_requested_at").desc(nulls_last=True), "role", "username")
    return render(request, "accounts/account_list.html", {"users": users})


@never_cache
@requires("accounts.manage")
@sensitive_variables()
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
@sensitive_variables()
def account_reset_password(request, pk):
    user = get_object_or_404(User, pk=pk)
    temporary_password = reset_password(user=user, reset_by=request.user)
    return render(
        request,
        "accounts/temporary_password.html",
        {
            "account": user,
            "created": False,
            **delivery_context(
                user=user, temporary_password=temporary_password, actor=request.user, purpose="reset"
            ),
        },
    )


@never_cache
@require_POST
@requires("accounts.manage")
@sensitive_variables()
def account_send_credentials(request, pk):
    """Email the temporary password that was just shown, saving the address first if it changed.

    Only the account's current temporary password can be sent: ``deliver_login_details`` checks
    it against the stored hash, so an old or typed-in password is never emailed.
    """
    user = get_object_or_404(User, pk=pk)
    form = SendCredentialsForm(request.POST)
    if not form.is_valid():
        temporary_password = request.POST.get("temporary_password", "")
        if not (user.must_change_password and temporary_password and user.check_password(temporary_password)):
            messages.error(request, "Those login details are no longer current. Reset the password again.")
            return redirect("account_list")
        return render(
            request,
            "accounts/temporary_password.html",
            {
                "account": user,
                "temporary_password": temporary_password,
                "purpose": request.POST.get("purpose", "reset"),
                "send_form": form,
            },
            status=400,
        )
    data = form.cleaned_data
    temporary_password = data["temporary_password"]
    if not (user.must_change_password and user.check_password(temporary_password)):
        messages.error(request, "Those login details are no longer current. Reset the password again.")
        return redirect("account_list")
    if data["email"] != user.email:
        with transaction.atomic():
            previous = user.email
            user.email = data["email"]
            user.save(update_fields=["email"])
            audit.record(
                "account.email.update",
                actor=request.user,
                target_type="User",
                target_id=user.pk,
                old_value={"email": masked_address(previous) if previous else ""},
                new_value={"email": masked_address(user.email)},
            )
    context = delivery_context(
        user=user, temporary_password=temporary_password, actor=request.user, purpose=data["purpose"]
    )
    return render(
        request,
        "accounts/temporary_password.html",
        {"account": user, "purpose": data["purpose"], "sent_from_page": True, **context},
    )


@never_cache
@require_POST
@requires("accounts.manage")
@sensitive_variables()
def account_resend_credentials(request, pk):
    user = get_object_or_404(User, pk=pk)
    try:
        temporary_password = reset_password(user=user, reset_by=request.user, temporary_only=True)
    except ValidationError as error:
        messages.error(request, " ".join(error.messages))
        return redirect("account_list")
    return render(
        request,
        "accounts/temporary_password.html",
        {
            "account": user,
            "created": False,
            "resent": True,
            **delivery_context(
                user=user, temporary_password=temporary_password, actor=request.user, purpose="resend"
            ),
        },
    )
