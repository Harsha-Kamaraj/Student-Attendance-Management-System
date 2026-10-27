"""Exercise OTP single-use guarantees and throttling with separate PostgreSQL connections."""

from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pyotp
from django.db import close_old_connections, connection, connections
from django.test import TransactionTestCase, override_settings, skipUnlessDBFeature

from . import otp
from .models import Role, User


@override_settings(
    OTP_REQUIRED=True,
    PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"],
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
)
@skipUnlessDBFeature("has_select_for_update")
class OTPConcurrencyTests(TransactionTestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="OTPTEST", password="Attend#2026", role=Role.STUDENT, email="student@example.com"
        )

    def _fixture_teardown(self):
        # The append-only audit trigger must be suspended only while flushing the test DB.
        if connection.vendor != "postgresql":
            return super()._fixture_teardown()
        with connection.cursor() as cursor:
            cursor.execute("ALTER TABLE audit_auditentry DISABLE TRIGGER audit_entry_no_truncate")
        try:
            super()._fixture_teardown()
        finally:
            with connection.cursor() as cursor:
                cursor.execute("ALTER TABLE audit_auditentry ENABLE TRIGGER audit_entry_no_truncate")

    def simultaneous(self, operation, count=2):
        barrier = Barrier(count)

        def worker():
            close_old_connections()
            try:
                user = User.objects.get(pk=self.user.pk)
                barrier.wait(timeout=10)
                return operation(user)
            finally:
                connections.close_all()

        with ThreadPoolExecutor(max_workers=count) as pool:
            futures = [pool.submit(worker) for _ in range(count)]
            return [future.result(timeout=20) for future in futures]

    def enroll(self):
        secret = otp.new_secret()
        codes = otp.confirm_setup(self.user, secret, pyotp.TOTP(secret).now())
        self.user.refresh_from_db()
        return codes

    def test_backup_code_can_be_consumed_only_once_concurrently(self):
        codes = self.enroll()
        results = self.simultaneous(lambda user: otp.verify_code(user, codes[0]))
        self.assertCountEqual(results, [(True, False), (False, False)])
        self.assertEqual(otp.remaining_backup_codes(self.user), 9)

    def test_parallel_email_requests_cannot_exceed_limit(self):
        self.enroll()

        def send(user):
            try:
                otp.send_email_code(user)
                return "sent"
            except otp.TooManyEmailCodes:
                return "limited"

        self.assertCountEqual(self.simultaneous(send, count=4), ["sent"] * 3 + ["limited"])
        self.assertEqual(self.user.otp_email_codes.count(), 3)

    def test_parallel_setup_cannot_replace_the_winning_secret(self):
        def setup(user):
            secret = otp.new_secret()
            try:
                otp.confirm_setup(user, secret, pyotp.TOTP(secret).now())
                return secret
            except otp.AlreadyConfigured:
                return None

        results = self.simultaneous(setup)
        self.assertEqual(results.count(None), 1)
        self.user.refresh_from_db()
        self.assertIn(self.user.otp_secret, results)
        self.assertEqual(otp.remaining_backup_codes(self.user), 10)
