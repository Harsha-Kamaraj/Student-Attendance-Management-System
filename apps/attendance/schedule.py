"""Today's timetabled classes, whether attendance is marked, and the next class (dashboards)."""

from dataclasses import dataclass
from datetime import date, datetime, time

from django.utils import timezone

from apps.academics.models import TeachingAssignment, TimetableSlot

from .models import PERIOD_SPANS, AttendanceSession, period_label


@dataclass(frozen=True)
class ScheduledClass:
    slot: TimetableSlot
    day: date
    marked: bool
    starts: time | None
    ends: time | None

    @property
    def assignment(self) -> TeachingAssignment:
        return self.slot.assignment

    @property
    def period(self) -> int:
        return self.slot.period

    @property
    def time_label(self) -> str:
        return period_label(self.slot.period)

    def state(self, now: time) -> str:
        """'marked', 'now', 'due' (finished but not marked) or 'upcoming'."""
        if self.marked:
            return "marked"
        if self.starts and self.ends and self.starts <= now < self.ends:
            return "now"
        if self.ends and now >= self.ends:
            return "due"
        return "upcoming"


def classes_on(day, assignments):
    """Timetabled classes on ``day`` for the given teaching assignments, in period order."""
    slots = list(
        TimetableSlot.objects.filter(assignment__in=assignments, weekday=day.weekday())
        .select_related("assignment__section", "assignment__subject", "assignment__faculty")
        .order_by("period", "assignment__subject__code")
    )
    marked = set(
        AttendanceSession.objects.filter(
            assignment__in={slot.assignment_id for slot in slots}, date=day
        ).values_list("assignment_id", "period")
    )
    return [
        ScheduledClass(
            slot=slot,
            day=day,
            marked=(slot.assignment_id, slot.period) in marked,
            starts=PERIOD_SPANS.get(slot.period, (None, None))[0],
            ends=PERIOD_SPANS.get(slot.period, (None, None))[1],
        )
        for slot in slots
    ]


def today_overview(assignments, now: datetime | None = None):
    """Rows for today's classes with their state, the next class to teach, and unmarked count."""
    now = timezone.localtime(now)
    rows = classes_on(now.date(), assignments)
    clock = now.time()
    states = [(row, row.state(clock)) for row in rows]
    upcoming = next(((row, state) for row, state in states if state in ("now", "upcoming")), (None, None))
    unmarked = sum(1 for _, state in states if state == "due")
    return {
        "today_rows": states,
        "next_class": upcoming[0],
        "next_class_now": upcoming[1] == "now",
        "unmarked_count": unmarked,
        "now": now,
    }
