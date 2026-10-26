"""Scoped attendance records and their read-only correction history (BL-16 / BL-18)."""

from django.core.paginator import Paginator
from django.shortcuts import render
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET

from apps.academics.models import Student, TeachingAssignment
from apps.accounts.permissions import (
    get_visible_or_deny,
    requires,
    visible_attendance_history,
    visible_attendance_records,
)

from .history_forms import AttendanceHistoryFilterForm
from .models import AttendanceRecord, Status

HISTORY_PAGE_SIZE = 25


def _query_without_page(request):
    query = request.GET.copy()
    query.pop("page", None)
    return query.urlencode()


def _check_filter_scope(form, field, model):
    """Use the normal 403/404 rules for IDs without querying malformed IDs."""
    raw_id = form.data.get(field, "")
    if (
        isinstance(raw_id, str)
        and raw_id.isascii()
        and raw_id.isdecimal()
        and len(raw_id) <= 19
        and 0 < int(raw_id) <= 9223372036854775807
    ):
        get_visible_or_deny(form.fields[field].queryset, model, int(raw_id))


@never_cache
@requires("attendance.history")
@require_GET
def attendance_history(request):
    form = AttendanceHistoryFilterForm(request.GET or None, user=request.user)
    records = visible_attendance_records(request.user).select_related(
        "student__user",
        "session__assignment__section",
        "session__assignment__subject",
        "session__recorded_by",
    )
    if request.GET:
        _check_filter_scope(form, "assignment", TeachingAssignment)
        _check_filter_scope(form, "student", Student)
        if form.is_valid():
            values = form.cleaned_data
            if values["assignment"]:
                records = records.filter(session__assignment=values["assignment"])
            if values["student"]:
                records = records.filter(student=values["student"])
            if values["start_date"]:
                records = records.filter(session__date__gte=values["start_date"])
            if values["end_date"]:
                records = records.filter(session__date__lte=values["end_date"])
            if values["period"]:
                records = records.filter(session__period=values["period"])
            if values["status"]:
                records = records.filter(status=values["status"])
        else:
            # An invalid filter must never silently fall back to all records.
            records = records.none()
    page = Paginator(
        records.order_by("-session__date", "-session__period", "student__roll_number", "-pk"),
        HISTORY_PAGE_SIZE,
    ).get_page(request.GET.get("page"))
    return render(
        request,
        "attendance/history.html",
        {
            "form": form,
            "page_obj": page,
            "query_string": _query_without_page(request),
            "filters_applied": bool(request.GET),
        },
    )


@never_cache
@requires("attendance.history")
@require_GET
def attendance_changes(request, pk):
    record = get_visible_or_deny(
        visible_attendance_records(request.user).select_related(
            "student__user",
            "session__assignment__section",
            "session__assignment__subject",
            "session__recorded_by",
        ),
        AttendanceRecord,
        pk,
    )
    changes = (
        visible_attendance_history(request.user)
        .filter(action="attendance.correct", target_type="AttendanceRecord", target_id=str(record.pk))
        .order_by("-timestamp", "-pk")
    )
    page = Paginator(changes, HISTORY_PAGE_SIZE).get_page(request.GET.get("page"))
    labels = dict(Status.choices)
    for entry in page:
        old = entry.old_value if isinstance(entry.old_value, dict) else {}
        new = entry.new_value if isinstance(entry.new_value, dict) else {}
        entry.old_status_label = labels.get(old.get("status"), "Unknown")
        entry.new_status_label = labels.get(new.get("status"), "Unknown")
    return render(
        request,
        "attendance/changes.html",
        {"record": record, "page_obj": page, "query_string": _query_without_page(request)},
    )
