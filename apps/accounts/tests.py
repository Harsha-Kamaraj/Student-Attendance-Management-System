from django.contrib.auth import get_user_model
from django.test import TestCase

from .models import User


class UserModelTests(TestCase):
    def test_project_uses_custom_user_model(self):
        self.assertIs(get_user_model(), User)

    def test_password_is_stored_hashed(self):
        user = User.objects.create_user(username="21CS001", password="Attend#2026")
        self.assertNotEqual(user.password, "Attend#2026")
        self.assertTrue(user.check_password("Attend#2026"))
