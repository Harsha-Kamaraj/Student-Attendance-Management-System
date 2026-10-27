"""Test runner: tests written before two-factor login (BL-33) log in with a password only.

OTP is switched off for them; the OTP tests switch it back on with override_settings.
The value configured for the app is kept in OTP_REQUIRED_CONFIGURED so a test can check
that OTP is on by default.
"""

from django.conf import settings
from django.test import override_settings
from django.test.runner import DiscoverRunner


class Runner(DiscoverRunner):
    def setup_test_environment(self, **kwargs):
        super().setup_test_environment(**kwargs)
        self.otp_settings = override_settings(
            OTP_REQUIRED_CONFIGURED=settings.OTP_REQUIRED, OTP_REQUIRED=False
        )
        self.otp_settings.enable()

    def teardown_test_environment(self, **kwargs):
        self.otp_settings.disable()
        super().teardown_test_environment(**kwargs)
