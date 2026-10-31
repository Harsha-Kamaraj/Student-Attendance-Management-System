from django import template

from apps.attendance.models import period_label as _period_label

register = template.Library()


@register.filter
def period_label(period):
    """Render a period number with its timetable slot, e.g. 'Period 1 (8:00–9:00 am)'."""
    return _period_label(period)
