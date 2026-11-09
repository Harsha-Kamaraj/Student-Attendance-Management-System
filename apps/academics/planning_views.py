"""Admin planning pages: the weekly timetable and semester class totals."""

from django import forms
from django.contrib import messages
from django.db import IntegrityError, transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_POST

from apps.accounts.forms import BootstrapMixin
from apps.accounts.permissions import requires
from apps.attendance.models import PERIOD_CHOICES
from apps.audit import services as audit

from .models import TeachingAssignment, TimetableSlot, Weekday


def _offerings():
    return TeachingAssignment.objects.select_related("section", "subject", "faculty").order_by(
        "section__class_name", "section__name", "section__year", "subject__code"
    )


class OfferingChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        teacher = obj.faculty.full_name if obj.faculty else "no teacher yet"
        return f"{obj.subject} — {obj.section} ({teacher})"


class TimetableSlotForm(BootstrapMixin, forms.Form):
    assignment = OfferingChoiceField(queryset=TeachingAssignment.objects.none(), label="Class")
    weekday = forms.TypedChoiceField(coerce=int, choices=Weekday.choices, label="Day")
    period = forms.TypedChoiceField(coerce=int, choices=PERIOD_CHOICES, label="Period")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["assignment"].queryset = _offerings()

    def clean(self):
        cleaned = super().clean()
        assignment, weekday, period = (cleaned.get(key) for key in ("assignment", "weekday", "period"))
        if assignment is None or weekday is None or period is None:
            return cleaned
        same_time = TimetableSlot.objects.filter(weekday=weekday, period=period).select_related(
            "assignment__subject", "assignment__section"
        )
        section_clash = same_time.filter(assignment__section=assignment.section).first()
        if section_clash:
            raise forms.ValidationError(
                f"{assignment.section} already has {section_clash.assignment.subject} at that time."
            )
        if assignment.faculty_id:
            teacher_clash = same_time.filter(assignment__faculty_id=assignment.faculty_id).first()
            if teacher_clash:
                raise forms.ValidationError(
                    f"{assignment.faculty.full_name} already teaches {teacher_clash.assignment.subject} "
                    f"in {teacher_clash.assignment.section} at that time."
                )
        return cleaned


@never_cache
@requires("sections.manage")
def timetable(request):
    """Admin keeps the weekly timetable that drives the faculty "today's classes" reminders."""
    form = TimetableSlotForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        data = form.cleaned_data
        try:
            with transaction.atomic():
                slot = TimetableSlot.objects.create(
                    assignment=data["assignment"], weekday=data["weekday"], period=data["period"]
                )
        except IntegrityError:
            form.add_error(None, "That class is already in the timetable at that time.")
        else:
            audit.record(
                "timetable.slot.add",
                actor=request.user,
                target_type="TimetableSlot",
                target_id=slot.pk,
                new_value={
                    "class": str(slot.assignment),
                    "day": slot.get_weekday_display(),
                    "period": slot.period,
                },
            )
            messages.success(request, f"Added {slot.assignment.subject} on {slot.get_weekday_display()}.")
            return redirect("timetable")
    slots = TimetableSlot.objects.select_related(
        "assignment__section", "assignment__subject", "assignment__faculty"
    ).order_by("weekday", "period", "assignment__section__class_name", "assignment__section__name")
    days = [(label, [slot for slot in slots if slot.weekday == value]) for value, label in Weekday.choices]
    return render(
        request,
        "academics/timetable.html",
        {"form": form, "days": days, "slot_count": len(slots)},
        status=400 if request.method == "POST" else 200,
    )


@never_cache
@require_POST
@requires("sections.manage")
def timetable_remove(request, pk):
    slot = get_object_or_404(TimetableSlot.objects.select_related("assignment__subject"), pk=pk)
    audit.record(
        "timetable.slot.remove",
        actor=request.user,
        target_type="TimetableSlot",
        target_id=slot.pk,
        old_value={"class": str(slot.assignment), "day": slot.get_weekday_display(), "period": slot.period},
    )
    slot.delete()
    messages.success(request, "Removed the class from the timetable.")
    return redirect("timetable")


@never_cache
@requires("sections.manage")
def semester_plan(request):
    """Admin sets how many classes each subject offering will hold this semester."""
    offerings = list(_offerings())
    errors = {}
    if request.method == "POST":
        changes = []
        for offering in offerings:
            raw = request.POST.get(f"planned_{offering.pk}", "").strip()
            if raw == "":
                value = None
            elif raw.isdigit() and 1 <= int(raw) <= 500:
                value = int(raw)
            else:
                errors[offering.pk] = "Enter a whole number from 1 to 500, or leave blank."
                continue
            if value != offering.planned_sessions:
                changes.append((offering, offering.planned_sessions, value))
        if not errors:
            with transaction.atomic():
                for offering, old, new in changes:
                    offering.planned_sessions = new
                    offering.save(update_fields=["planned_sessions"])
                    audit.record(
                        "semester_plan.update",
                        actor=request.user,
                        target_type="TeachingAssignment",
                        target_id=offering.pk,
                        old_value={"planned_sessions": old},
                        new_value={"planned_sessions": new},
                    )
            messages.success(
                request,
                f"Saved semester classes for {len(changes)} class{'es' if len(changes) != 1 else ''}.",
            )
            return redirect("semester_plan")
    rows = [
        {
            "offering": offering,
            "value": request.POST.get(f"planned_{offering.pk}", "")
            if request.method == "POST"
            else (offering.planned_sessions or ""),
            "error": errors.get(offering.pk),
        }
        for offering in offerings
    ]
    return render(
        request,
        "academics/semester_plan.html",
        {"rows": rows},
        status=400 if errors else 200,
    )
