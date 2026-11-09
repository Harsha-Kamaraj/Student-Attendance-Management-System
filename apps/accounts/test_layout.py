"""Shared page layout: the sidebar lists only each role's own pages and marks the current one."""

from django.test import TestCase
from django.urls import reverse

from apps.academics.tests import make_faculty, make_student

from .models import Role, User
from .templatetags.ui import SIDEBAR, icon


def sidebar_html(response):
    """Return only the sidebar part of a rendered page."""
    page = response.content.decode()
    start = page.index('<aside class="app-sidebar"')
    return page[start : page.index("</aside>", start)]


class SidebarTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = User.objects.create_user(username="ADMIN1", role=Role.ADMIN)
        cls.faculty = make_faculty("F001")
        cls.student = make_student("S001")

    def open(self, user, url_name):
        self.client.force_login(user)
        return self.client.get(reverse(url_name))

    def test_every_sidebar_link_opens_for_its_role(self):
        users = {Role.ADMIN: self.admin, Role.FACULTY: self.faculty.user, Role.STUDENT: self.student.user}
        for role, sections in SIDEBAR.items():
            self.client.force_login(users[role])
            for _title, links in sections:
                for url_name, label, _icon, _extra in links:
                    with self.subTest(role=role, link=label):
                        response = self.client.get(reverse(url_name), follow=True)
                        self.assertEqual(response.status_code, 200)

    def test_student_sidebar_has_no_staff_pages(self):
        nav = sidebar_html(self.open(self.student.user, "dashboard_student"))
        self.assertIn(reverse("attendance_summary"), nav)
        for url_name in ("student_list", "faculty_list", "attendance_mark", "backup_list", "account_list"):
            self.assertNotIn(f'href="{reverse(url_name)}"', nav)

    def test_faculty_sidebar_has_no_admin_settings(self):
        nav = sidebar_html(self.open(self.faculty.user, "dashboard_faculty"))
        self.assertIn(reverse("attendance_mark"), nav)
        admin_only = ("faculty_list", "backup_list", "threshold_settings", "account_create", "section_list")
        for url_name in admin_only:
            self.assertNotIn(f'href="{reverse(url_name)}"', nav)

    def test_current_page_is_marked_and_longest_match_wins(self):
        nav = sidebar_html(self.open(self.admin, "account_create"))
        self.assertEqual(nav.count('aria-current="page"'), 1)
        current = nav[: nav.index('aria-current="page"')]
        self.assertTrue(current.rstrip().endswith(f'href="{reverse("account_create")}"'))

    def test_sign_in_pages_have_no_sidebar(self):
        self.assertNotContains(self.client.get(reverse("login")), "app-sidebar")
        self.assertContains(self.client.get(reverse("login")), "img/logo.svg")

    def test_unknown_icon_renders_empty_and_hidden_from_screen_readers(self):
        html = icon("no-such-icon")
        self.assertIn('aria-hidden="true"', html)
        self.assertTrue(html.endswith("></svg>"))
