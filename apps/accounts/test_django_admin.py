"""Django admin site checks. Until BL-07/BL-08 add in-app buttons, the Django admin is
where accounts are deactivated and reactivated (manual test steps 21-24)."""

from django.test import TestCase

from .models import Role, User

PASSWORD = "Attend#2026"


class DjangoAdminTests(TestCase):
    def setUp(self):
        self.superuser = User.objects.create_superuser(username="root", password=PASSWORD)
        self.student = User.objects.create_user(username="21CS001", password=PASSWORD, role=Role.STUDENT)
        self.client.login(username="root", password=PASSWORD)
        self.change_url = f"/admin/accounts/user/{self.student.pk}/change/"

    def change_form_data(self, **overrides):
        form = self.client.get(self.change_url).context["adminform"].form
        skip = {"password", "groups", "user_permissions", "last_login", "date_joined", "is_active"}
        data = {k: v for k, v in form.initial.items() if v is not None and k not in skip}
        joined = self.student.date_joined
        data |= {
            "date_joined_0": joined.date(),
            "date_joined_1": joined.strftime("%H:%M:%S"),
            "last_login_0": "",
            "last_login_1": "",
        }
        return data | overrides

    def test_admin_pages_load(self):
        for url in ("/admin/", "/admin/accounts/user/", "/admin/accounts/user/add/", self.change_url):
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 200)

    def test_deactivate_and_reactivate(self):
        response = self.client.post(self.change_url, self.change_form_data())
        self.assertEqual(response.status_code, 302)
        self.student.refresh_from_db()
        self.assertFalse(self.student.is_active)

        self.client.post(self.change_url, self.change_form_data(is_active="on"))
        self.student.refresh_from_db()
        self.assertTrue(self.student.is_active)

    def test_add_user_with_role(self):
        self.client.post(
            "/admin/accounts/user/add/",
            {
                "username": "f009",
                "password1": "Fac#Pass2026",
                "password2": "Fac#Pass2026",
                "usable_password": "true",
                "role": Role.FACULTY,
            },
        )
        self.assertTrue(User.objects.filter(username="F009", role=Role.FACULTY).exists())

    def test_non_staff_app_admin_cannot_use_django_admin(self):
        User.objects.create_user(username="ADMIN1", password=PASSWORD, role=Role.ADMIN)
        self.client.logout()
        self.client.login(username="ADMIN1", password=PASSWORD)
        response = self.client.get("/admin/accounts/user/")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/admin/login/", response["Location"])
