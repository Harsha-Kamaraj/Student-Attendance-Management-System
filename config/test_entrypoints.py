"""The WSGI and ASGI entry points that a production web server loads (Part 3 coverage)."""

import importlib

from django.test import SimpleTestCase


class ServerEntryPointTests(SimpleTestCase):
    def test_wsgi_and_asgi_modules_expose_a_callable_application(self):
        for name in ("config.wsgi", "config.asgi"):
            with self.subTest(module=name):
                module = importlib.import_module(name)
                self.assertTrue(callable(module.application))
