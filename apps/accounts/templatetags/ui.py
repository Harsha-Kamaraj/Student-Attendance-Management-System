"""Layout helpers shared by every page: inline icons and the role-based sidebar."""

from django import template
from django.urls import reverse
from django.utils.html import format_html
from django.utils.safestring import mark_safe

from apps.accounts.models import Role

register = template.Library()

# Simple 24x24 stroke icons drawn with the current text colour. Kept inline so pages need
# no icon font or external request.
ICONS = {
    "dashboard": (
        '<rect x="3" y="3" width="7" height="9" rx="1"/>',
        '<rect x="14" y="3" width="7" height="5" rx="1"/>',
        '<rect x="14" y="12" width="7" height="9" rx="1"/>',
        '<rect x="3" y="16" width="7" height="5" rx="1"/>',
    ),
    "users": (
        '<path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/>',
        '<circle cx="9" cy="7" r="4"/>',
        '<path d="M22 21v-2a4 4 0 0 0-3-3.87"/>',
        '<path d="M16 3.13a4 4 0 0 1 0 7.75"/>',
    ),
    "user": (
        '<path d="M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2"/>',
        '<circle cx="12" cy="7" r="4"/>',
    ),
    "user-plus": (
        '<path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/>',
        '<circle cx="9" cy="7" r="4"/>',
        '<path d="M19 8v6"/>',
        '<path d="M22 11h-6"/>',
    ),
    "cap": (
        '<path d="M22 10 12 5 2 10l10 5 10-5z"/>',
        '<path d="M6 12v5c3 3 9 3 12 0v-5"/>',
    ),
    "book": (
        '<path d="M2 4h6a4 4 0 0 1 4 4v13a3 3 0 0 0-3-3H2z"/>',
        '<path d="M22 4h-6a4 4 0 0 0-4 4v13a3 3 0 0 1 3-3h7z"/>',
    ),
    "layers": (
        '<path d="m12 2 10 5-10 5L2 7z"/>',
        '<path d="m2 17 10 5 10-5"/>',
        '<path d="m2 12 10 5 10-5"/>',
    ),
    "board": (
        '<path d="M2 3h20"/>',
        '<path d="M21 3v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V3"/>',
        '<path d="m7 21 5-5 5 5"/>',
    ),
    "clipboard": (
        '<rect x="8" y="2" width="8" height="4" rx="1"/>',
        '<path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2"/>',
        '<path d="m9 14 2 2 4-4"/>',
    ),
    "history": (
        '<path d="M3 12a9 9 0 1 0 2.64-6.36L3 8"/>',
        '<path d="M3 3v5h5"/>',
        '<path d="M12 7v5l4 2"/>',
    ),
    "chart": (
        '<path d="M3 3v18h18"/>',
        '<path d="M18 17V9"/>',
        '<path d="M13 17V5"/>',
        '<path d="M8 17v-3"/>',
    ),
    "trend-down": (
        '<path d="m22 17-8.5-8.5-5 5L2 7"/>',
        '<path d="M16 17h6v-6"/>',
    ),
    "bell": (
        '<path d="M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9"/>',
        '<path d="M10.3 21a1.94 1.94 0 0 0 3.4 0"/>',
    ),
    "shield": (
        '<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>',
        '<path d="m9 12 2 2 4-4"/>',
    ),
    "sliders": (
        '<path d="M4 21v-7"/>',
        '<path d="M4 10V3"/>',
        '<path d="M12 21v-9"/>',
        '<path d="M12 8V3"/>',
        '<path d="M20 21v-5"/>',
        '<path d="M20 12V3"/>',
        '<path d="M1 14h6"/>',
        '<path d="M9 8h6"/>',
        '<path d="M17 16h6"/>',
    ),
    "calendar": (
        '<rect x="3" y="4" width="18" height="18" rx="2"/>',
        '<path d="M16 2v4"/>',
        '<path d="M8 2v4"/>',
        '<path d="M3 10h18"/>',
    ),
    "database": (
        '<ellipse cx="12" cy="5" rx="9" ry="3"/>',
        '<path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"/>',
        '<path d="M3 12c0 1.66 4 3 9 3s9-1.34 9-3"/>',
    ),
    "alert": (
        '<path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3z"/>',
        '<path d="M12 9v4"/>',
        '<path d="M12 17h.01"/>',
    ),
    "key": (
        '<circle cx="7.5" cy="15.5" r="5.5"/>',
        '<path d="m21 2-9.6 9.6"/>',
        '<path d="m15.5 7.5 3 3L22 7l-3-3"/>',
    ),
    "logout": (
        '<path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/>',
        '<path d="m16 17 5-5-5-5"/>',
        '<path d="M21 12H9"/>',
    ),
    "menu": (
        '<path d="M4 6h16"/>',
        '<path d="M4 12h16"/>',
        '<path d="M4 18h16"/>',
    ),
    "pie": (
        '<path d="M21.21 15.89A10 10 0 1 1 8 2.83"/>',
        '<path d="M22 12A10 10 0 0 0 12 2v10z"/>',
    ),
    "check-circle": (
        '<path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/>',
        '<path d="m22 4-10 10.01-3-3"/>',
    ),
    "arrow-right": (
        '<path d="M5 12h14"/>',
        '<path d="m12 5 7 7-7 7"/>',
    ),
    "arrow-left": (
        '<path d="M19 12H5"/>',
        '<path d="m12 19-7-7 7-7"/>',
    ),
    "clock": (
        '<circle cx="12" cy="12" r="10"/>',
        '<path d="M12 6v6l4 2"/>',
    ),
    "target": (
        '<circle cx="12" cy="12" r="10"/>',
        '<circle cx="12" cy="12" r="6"/>',
        '<circle cx="12" cy="12" r="2"/>',
    ),
    "lock": (
        '<rect x="3" y="11" width="18" height="11" rx="2"/>',
        '<path d="M7 11V7a5 5 0 0 1 10 0v4"/>',
    ),
}


@register.simple_tag
def icon(name, size=20, css_class="icon"):
    """Render one inline icon; it is decorative, so screen readers skip it."""
    return format_html(
        '<svg class="{}" width="{}" height="{}" viewBox="0 0 24 24" fill="none" '
        'stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" '
        'aria-hidden="true" focusable="false">'
        "{}</svg>",
        css_class,
        size,
        size,
        mark_safe("".join(ICONS.get(name, ()))),  # noqa: S308 - fixed strings defined above, never user input
    )


# Sidebar entries per role: (section title, [(url name, label, icon, extra path prefixes)]).
# Labels match the dashboard wording, and each role only sees pages it may open.
SIDEBAR = {
    Role.ADMIN: [
        ("Overview", [("dashboard", "Dashboard", "dashboard", ())]),
        (
            "People",
            [
                ("student_list", "Students", "cap", ()),
                ("faculty_list", "Faculty", "users", ()),
                ("account_list", "Accounts and resets", "key", ()),
                ("account_create", "Create Admin account", "user-plus", ()),
            ],
        ),
        (
            "Classes",
            [
                ("section_list", "Classes and sections", "layers", ()),
                ("subject_list", "Subjects", "book", ()),
                ("timetable", "Timetable", "clock", ()),
                ("semester_plan", "Semester classes", "target", ()),
            ],
        ),
        (
            "Attendance",
            [
                ("attendance_history", "History and corrections", "history", ("/attendance/records/",)),
                ("attendance_mark", "Record missed attendance", "clipboard", ()),
                ("attendance_report", "Reports", "chart", ()),
                ("shortage_list", "Below threshold", "trend-down", ()),
            ],
        ),
        (
            "Settings",
            [
                ("threshold_settings", "Attendance threshold", "sliders", ()),
                ("correction_window_settings", "Correction window", "calendar", ()),
                ("backup_list", "Backup and recovery", "database", ()),
            ],
        ),
        ("Account", [("my_profile", "My profile", "user", ())]),
    ],
    Role.FACULTY: [
        ("Overview", [("dashboard", "Dashboard", "dashboard", ())]),
        (
            "Teaching",
            [
                ("attendance_mark", "Mark attendance", "clipboard", ()),
                ("my_classes", "My classes", "board", ()),
                ("student_list", "Students in my classes", "cap", ()),
                ("subject_list", "My subjects", "book", ()),
            ],
        ),
        (
            "Attendance",
            [
                ("attendance_history", "History and corrections", "history", ("/attendance/records/",)),
                ("attendance_report", "Reports", "chart", ()),
                ("shortage_list", "Below threshold", "trend-down", ()),
            ],
        ),
        ("Account", [("my_profile", "My profile", "user", ())]),
    ],
    Role.STUDENT: [
        ("Overview", [("dashboard", "Dashboard", "dashboard", ())]),
        (
            "Attendance",
            [
                ("attendance_summary", "My attendance", "pie", ()),
                ("notification_list", "Notifications", "bell", ()),
            ],
        ),
        ("Account", [("my_profile", "My profile", "user", ())]),
    ],
}


@register.inclusion_tag("includes/sidebar.html", takes_context=True)
def sidebar(context):
    """Build the sidebar for the signed-in user and mark the page they are on.

    The longest matching path wins, so /users/create/ highlights "Create Admin account"
    rather than "Accounts and resets".
    """
    request = context["request"]
    user = request.user
    path = request.path
    sections = []
    best = (0, None)
    for title, entries in SIDEBAR.get(user.role, []):
        links = []
        for url_name, label, icon_name, extra in entries:
            href = reverse(url_name)
            prefixes = (href, "/dashboard/") if url_name == "dashboard" else (href, *extra)
            for prefix in prefixes:
                if path.startswith(prefix) and len(prefix) > best[0]:
                    best = (len(prefix), href)
            badge = url_name == "notification_list"
            links.append({"href": href, "label": label, "icon": icon_name, "badge": badge})
        sections.append({"title": title, "links": links})
    for section in sections:
        for link in section["links"]:
            link["active"] = link["href"] == best[1]
    return {"sections": sections, "unread_notification_count": context.get("unread_notification_count")}
