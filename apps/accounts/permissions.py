"""Who may do what (BL-05). See Documents/BL-05_Permission_Matrix.md.

Two layers:
1. Role permissions: may this role perform the action at all? (`has_permission`)
2. Scope: which records may this user see or change? (`visible_*`, `can_*`)

Every view must check both on the server (SEC-10). Hiding a button is not enough.
"""

from functools import wraps

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import CharField
from django.db.models.functions import Cast
from django.http import Http404

from apps.academics.models import Student, Subject, TeachingAssignment
from apps.attendance.models import AttendanceRecord
from apps.audit.models import AuditEntry

from .models import Role

ADMIN, FACULTY, STUDENT = Role.ADMIN, Role.FACULTY, Role.STUDENT

# Role-level permission matrix. Scope limits (own classes, own records) are applied
# by the scope functions below.
PERMISSIONS = {
    "accounts.manage": {ADMIN},  # create, reset, deactivate, delete accounts (AR-01, AR-02)
    "students.manage": {ADMIN},  # add, update, deactivate, reactivate, delete (FR-03, AR-02)
    "students.view": {ADMIN, FACULTY, STUDENT},  # faculty: own classes; student: self
    "faculty.manage": {ADMIN},  # FR-04, SEC-14
    "subjects.create": {ADMIN, FACULTY},  # FR-05
    "subjects.edit": {ADMIN, FACULTY},  # faculty: subjects they teach
    "subjects.delete": {ADMIN},  # BL-05 decision
    "sections.manage": {ADMIN},  # sections, enrolments, teaching assignments (FR-06, SEC-14)
    "attendance.mark": {ADMIN, FACULTY},  # faculty: own classes; admin: missed sessions with reason (AR-08)
    "attendance.correct": {ADMIN, FACULTY},  # faculty: own classes in window; admin: any, with reason (AR-08)
    "attendance.view": {ADMIN, FACULTY, STUDENT},  # faculty: own classes; student: self (FR-09)
    "attendance.history": {ADMIN, FACULTY},  # faculty: own classes (BL-05 decision)
    "reports.generate": {ADMIN, FACULTY},  # faculty: own classes (UC-09)
    "reports.export": {ADMIN, FACULTY},  # faculty: own classes (FR-16)
    "records.search": {ADMIN, FACULTY},  # faculty: own classes (UC-11)
    "threshold.configure": {ADMIN},  # SEC-14
    "low_attendance.view": {ADMIN, FACULTY},  # faculty: own classes (AR-14)
    "backup.manage": {ADMIN},  # FR-19, SEC-26
    "audit.view": {ADMIN},  # full audit log
}


def has_permission(user, action):
    if action not in PERMISSIONS:
        raise KeyError(f"Unknown permission: {action}")
    return bool(user and user.is_authenticated and user.is_active and user.role in PERMISSIONS[action])


def requires(action):
    """View decorator: logged-in users whose role has `action`; others get 403 (logged)."""

    def decorator(view):
        @wraps(view)
        @login_required
        def wrapped(request, *args, **kwargs):
            if not has_permission(request.user, action):
                raise PermissionDenied(action)
            return view(request, *args, **kwargs)

        return wrapped

    return decorator


# --- Scope: which records a user may see -------------------------------------------------


def _faculty_assignments(user):
    return TeachingAssignment.objects.filter(faculty__user=user)


def visible_assignments(user):
    if user.role == ADMIN:
        return TeachingAssignment.objects.all()
    if user.role == FACULTY:
        return _faculty_assignments(user)
    if user.role == STUDENT:
        return TeachingAssignment.objects.filter(enrollments__student__user=user).distinct()
    return TeachingAssignment.objects.none()


def visible_students(user):
    if user.role == ADMIN:
        return Student.objects.all()
    if user.role == FACULTY:
        return Student.objects.filter(enrollments__assignment__faculty__user=user).distinct()
    if user.role == STUDENT:
        return Student.objects.filter(user=user)
    return Student.objects.none()


def visible_attendance_records(user):
    if user.role == ADMIN:
        return AttendanceRecord.objects.all()
    if user.role == FACULTY:
        return AttendanceRecord.objects.filter(session__assignment__faculty__user=user)
    if user.role == STUDENT:
        return AttendanceRecord.objects.filter(student__user=user)
    return AttendanceRecord.objects.none()


def visible_attendance_history(user):
    """Audit entries about attendance records: Admin all, Faculty own classes, Students none."""
    if user.role == ADMIN:
        return AuditEntry.objects.all()
    if user.role == FACULTY:
        own = visible_attendance_records(user).annotate(pk_text=Cast("pk", CharField())).values("pk_text")
        return AuditEntry.objects.filter(target_type="AttendanceRecord", target_id__in=own)
    return AuditEntry.objects.none()


# --- Scope: what a user may change --------------------------------------------------------


def can_mark_attendance(user, assignment):
    if not has_permission(user, "attendance.mark"):
        return False
    return user.role == ADMIN or _faculty_assignments(user).filter(pk=assignment.pk).exists()


def can_correct_attendance(user, record):
    """Role and assignment scope; the BL-17 service enforces the deadline under locks."""
    if not has_permission(user, "attendance.correct"):
        return False
    return user.role == ADMIN or _faculty_assignments(user).filter(pk=record.session.assignment_id).exists()


def can_edit_subject(user, subject):
    if not has_permission(user, "subjects.edit"):
        return False
    return user.role == ADMIN or _faculty_assignments(user).filter(subject=subject).exists()


def can_delete_subject(user, subject: Subject):
    return has_permission(user, "subjects.delete")


# --- Enforcement helper -------------------------------------------------------------------


def get_visible_or_deny(queryset_for_user, model, pk):
    """Fetch one record the user may see.

    Missing record: 404. Existing but outside the user's scope: 403 "Access denied",
    logged, with no data returned (SEC-12, BL-05 decision).
    """
    try:
        return queryset_for_user.get(pk=pk)
    except model.DoesNotExist:
        if model.objects.filter(pk=pk).exists():
            raise PermissionDenied(f"{model.__name__} outside user scope") from None
        raise Http404 from None
