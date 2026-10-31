"""BL-30: shared pages must start with a valid doctype, without Markdown fences."""

from django.test import TestCase


class DocumentModeTests(TestCase):
    def test_public_and_login_pages_begin_with_a_real_html_doctype(self):
        for path in ("/", "/login/"):
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 200)
                self.assertTrue(response.content.lstrip().lower().startswith(b"<!doctype html>"))
                self.assertNotIn(b"```", response.content)
