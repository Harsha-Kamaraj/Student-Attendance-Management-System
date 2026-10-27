"""Attendance reports and CSV/PDF exports for administrators and faculty."""

import csv
from io import BytesIO

from django import forms
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.http import HttpResponse
from django.shortcuts import render
from django.utils import timezone
from django.views.decorators.http import require_GET
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from apps.accounts.permissions import requires, visible_assignments

from .calculations import AttendanceTotals
from .models import AttendanceRecord, AttendanceSession, Status


class AttendanceReportFilterForm(forms.Form):
    """Form for filtering attendance reports."""

    start_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={"type": "date", "class": "form-control"}),
    )
    end_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={"type": "date", "class": "form-control"}),
    )
    assignment = forms.ModelChoiceField(
        queryset=None,
        required=False,
        empty_label="All authorized classes and subjects",
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    status = forms.ChoiceField(
        required=False,
        choices=[("", "All statuses"), *Status.choices],
        widget=forms.Select(attrs={"class": "form-select"}),
    )

    def __init__(self, *args, user, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["assignment"].queryset = (
            visible_assignments(user)
            .select_related("section", "subject")
            .order_by(
                "section__class_name",
                "section__name",
                "subject__code",
            )
        )

    def clean(self):
        cleaned = super().clean()

        start_date = cleaned.get("start_date")
        end_date = cleaned.get("end_date")

        if start_date and end_date and start_date > end_date:
            self.add_error(
                "end_date",
                "End date must be on or after the start date.",
            )

        return cleaned


def _filtered_records(request, form):
    """Return records and sessions restricted to authorized assignments."""

    assignments = visible_assignments(request.user)

    records = AttendanceRecord.objects.filter(session__assignment__in=assignments).select_related(
        "student",
        "session__assignment__section",
        "session__assignment__subject",
    )

    sessions = AttendanceSession.objects.filter(assignment__in=assignments)

    if request.GET:
        if not form.is_valid():
            return records.none(), sessions.none()

        filters = form.cleaned_data

        if filters["start_date"]:
            records = records.filter(session__date__gte=filters["start_date"])
            sessions = sessions.filter(date__gte=filters["start_date"])

        if filters["end_date"]:
            records = records.filter(session__date__lte=filters["end_date"])
            sessions = sessions.filter(date__lte=filters["end_date"])

        if filters["assignment"]:
            records = records.filter(session__assignment=filters["assignment"])
            sessions = sessions.filter(assignment=filters["assignment"])

        if filters["status"]:
            records = records.filter(status=filters["status"])

    return records, sessions


def _report_rows(records):
    """Group attendance records by student, section, and subject."""

    grouped_records = (
        records.order_by()
        .values(
            "student__roll_number",
            "student__full_name",
            "session__assignment__section__class_name",
            "session__assignment__section__name",
            "session__assignment__subject__code",
            "session__assignment__subject__name",
        )
        .annotate(
            held=Count("pk"),
            present=Count(
                "pk",
                filter=Q(status=Status.PRESENT),
            ),
            absent=Count(
                "pk",
                filter=Q(status=Status.ABSENT),
            ),
        )
        .order_by(
            "student__roll_number",
            "session__assignment__section__class_name",
            "session__assignment__section__name",
            "session__assignment__subject__code",
        )
    )

    rows = []

    for row in grouped_records:
        totals = AttendanceTotals(
            attended=row["present"],
            held=row["held"],
        )

        rows.append(
            {
                **row,
                "percentage": totals.percentage,
            }
        )

    return rows


@require_GET
@requires("reports.generate")
def attendance_report(request):
    """Display an attendance report for authorized users."""

    form = AttendanceReportFilterForm(
        request.GET or None,
        user=request.user,
    )

    records, sessions = _filtered_records(request, form)

    totals = records.aggregate(
        held=Count("pk"),
        present=Count(
            "pk",
            filter=Q(status=Status.PRESENT),
        ),
        absent=Count(
            "pk",
            filter=Q(status=Status.ABSENT),
        ),
    )

    overall = AttendanceTotals(
        attended=totals["present"],
        held=totals["held"],
    )

    report_rows = _report_rows(records)

    page = Paginator(report_rows, 50).get_page(request.GET.get("page"))

    context = {
        "form": form,
        "page_obj": page,
        "overall": overall,
        "present_count": totals["present"],
        "absent_count": totals["absent"],
        "session_count": sessions.count(),
        "generated_at": timezone.localtime(),
    }

    return render(
        request,
        "attendance/report.html",
        context,
    )


@require_GET
@requires("reports.export")
def attendance_report_csv(request):
    """Export matching authorized attendance report rows to CSV."""

    form = AttendanceReportFilterForm(
        request.GET or None,
        user=request.user,
    )

    records, _sessions = _filtered_records(request, form)

    response = HttpResponse(content_type="text/csv; charset=utf-8")

    response["Content-Disposition"] = 'attachment; filename="attendance_report.csv"'

    response.write("\ufeff")

    writer = csv.writer(response)

    writer.writerow(
        [
            "Roll Number",
            "Student Name",
            "Class",
            "Section",
            "Subject Code",
            "Subject Name",
            "Classes Held",
            "Present",
            "Absent",
            "Attendance Percentage",
        ]
    )

    for row in _report_rows(records):
        percentage = row["percentage"]

        writer.writerow(
            [
                row["student__roll_number"],
                row["student__full_name"],
                row["session__assignment__section__class_name"],
                row["session__assignment__section__name"],
                row["session__assignment__subject__code"],
                row["session__assignment__subject__name"],
                row["held"],
                row["present"],
                row["absent"],
                (f"{percentage:.2f}" if percentage is not None else "N/A"),
            ]
        )

    return response


@require_GET
@requires("reports.export")
def attendance_report_pdf(request):
    """Export matching authorized attendance report rows to PDF."""

    form = AttendanceReportFilterForm(
        request.GET or None,
        user=request.user,
    )

    records, sessions = _filtered_records(request, form)
    rows = _report_rows(records)

    buffer = BytesIO()

    document = SimpleDocTemplate(
        buffer,
        pagesize=landscape(A4),
        rightMargin=12 * mm,
        leftMargin=12 * mm,
        topMargin=12 * mm,
        bottomMargin=12 * mm,
        title="Attendance Report",
        author="Student Attendance Management System",
    )

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "ReportTitle",
        parent=styles["Title"],
        alignment=TA_CENTER,
        fontSize=18,
        leading=22,
        spaceAfter=8,
    )

    subtitle_style = ParagraphStyle(
        "ReportSubtitle",
        parent=styles["Normal"],
        alignment=TA_CENTER,
        fontSize=9,
        leading=12,
        textColor=colors.HexColor("#555555"),
        spaceAfter=12,
    )

    elements = [
        Paragraph("Attendance Report", title_style),
        Paragraph(
            (f"Generated: {timezone.localtime():%d %b %Y, %H:%M} | Attendance sessions: {sessions.count()}"),
            subtitle_style,
        ),
        Spacer(1, 4 * mm),
    ]

    totals = records.aggregate(
        held=Count("pk"),
        present=Count(
            "pk",
            filter=Q(status=Status.PRESENT),
        ),
        absent=Count(
            "pk",
            filter=Q(status=Status.ABSENT),
        ),
    )

    overall = AttendanceTotals(
        attended=totals["present"],
        held=totals["held"],
    )

    overall_percentage = f"{overall.percentage:.2f}%" if overall.percentage is not None else "N/A"

    summary_data = [
        ["Attendance records", "Present", "Absent", "Attendance %"],
        [
            str(totals["held"]),
            str(totals["present"]),
            str(totals["absent"]),
            overall_percentage,
        ],
    ]

    summary_table = Table(
        summary_data,
        colWidths=[55 * mm, 45 * mm, 45 * mm, 55 * mm],
    )

    summary_table.setStyle(
        TableStyle(
            [
                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, 0),
                    colors.HexColor("#24476B"),
                ),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTNAME", (0, 1), (-1, 1), "Helvetica"),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
            ]
        )
    )

    elements.extend(
        [
            summary_table,
            Spacer(1, 8 * mm),
            Paragraph("Student Attendance Details", styles["Heading2"]),
            Spacer(1, 3 * mm),
        ]
    )

    table_data = [
        [
            "Roll Number",
            "Student Name",
            "Class",
            "Section",
            "Subject Code",
            "Subject Name",
            "Held",
            "Present",
            "Absent",
            "Attendance %",
        ]
    ]

    for row in rows:
        percentage = row["percentage"]

        table_data.append(
            [
                str(row["student__roll_number"] or ""),
                str(row["student__full_name"] or ""),
                str(row["session__assignment__section__class_name"] or ""),
                str(row["session__assignment__section__name"] or ""),
                str(row["session__assignment__subject__code"] or ""),
                str(row["session__assignment__subject__name"] or ""),
                str(row["held"]),
                str(row["present"]),
                str(row["absent"]),
                (f"{percentage:.2f}%" if percentage is not None else "N/A"),
            ]
        )

    column_widths = [
        23 * mm,
        34 * mm,
        28 * mm,
        16 * mm,
        23 * mm,
        40 * mm,
        13 * mm,
        16 * mm,
        16 * mm,
        24 * mm,
    ]

    details_table = Table(
        table_data,
        colWidths=column_widths,
        repeatRows=1,
        hAlign="LEFT",
    )

    details_table.setStyle(
        TableStyle(
            [
                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, 0),
                    colors.HexColor("#24476B"),
                ),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 0), (-1, -1), 7),
                ("LEADING", (0, 0), (-1, -1), 9),
                ("ALIGN", (6, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                (
                    "ROWBACKGROUNDS",
                    (0, 1),
                    (-1, -1),
                    [colors.white, colors.HexColor("#F1F5F9")],
                ),
            ]
        )
    )

    elements.append(details_table)

    if not rows:
        elements.append(
            Paragraph(
                "No attendance records match the selected filters.",
                styles["Normal"],
            )
        )

    document.build(elements)

    pdf = buffer.getvalue()
    buffer.close()

    response = HttpResponse(
        pdf,
        content_type="application/pdf",
    )
    response["Content-Disposition"] = 'attachment; filename="attendance_report.pdf"'

    return response
