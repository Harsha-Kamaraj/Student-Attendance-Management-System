from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.test import TestCase

from .models import Role, User


class UserModelTests(TestCase):
    def test_project_uses_custom_user_model(self):
        self.assertIs(get_user_model(), User)

    def test_password_is_stored_hashed(self):
        user = User.objects.create_user(username="21CS001", password="Attend#2026", role=Role.STUDENT)
        self.assertNotEqual(user.password, "Attend#2026")
        self.assertTrue(user.check_password("Attend#2026"))

    def test_superuser_gets_admin_role(self):
        admin = User.objects.create_superuser(username="admin1", password="Attend#2026")
        self.assertEqual(admin.role, Role.ADMIN)

    def test_unknown_role_is_rejected(self):
        with transaction.atomic(), self.assertRaises(IntegrityError):
            User.objects.create_user(username="x1", password="Attend#2026", role="GUEST")

    def test_missing_role_is_rejected(self):
        with transaction.atomic(), self.assertRaises(IntegrityError):
            User.objects.create_user(username="x2", password="Attend#2026")

    def test_username_is_unique(self):
        User.objects.create_user(username="21CS001", password="Attend#2026", role=Role.STUDENT)
        with transaction.atomic(), self.assertRaises(IntegrityError):
            User.objects.create_user(username="21CS001", password="Attend#2026", role=Role.STUDENT)
