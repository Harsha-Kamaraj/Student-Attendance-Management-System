"""BL-29 availability evidence must never turn missing observations into uptime."""

from datetime import UTC, datetime, timedelta
from unittest.mock import patch

from django.db import OperationalError
from django.test import SimpleTestCase, TestCase, override_settings
from django.urls import reverse

from apps.accounts.models import Role, User
from apps.backups.locks import BackupBusy
from verification.availability import business_slots, probe, summarize


class MonthlyAvailabilityTests(SimpleTestCase):
    month = "2026-02"
    after_month = datetime(2026, 3, 1, tzinfo=UTC)

    def observations(self):
        slots, _ = business_slots(self.month, 300)
        return [{"observed_at": start.isoformat(), "status": "up"} for start, _ in slots]

    def test_slots_use_ist_business_hours_and_exclude_sundays(self):
        slots, _ = business_slots(self.month, 300)
        self.assertEqual(len(slots), 24 * 10 * 12)
        self.assertEqual(slots[0][0], datetime(2026, 2, 2, 2, 30, tzinfo=UTC))
        self.assertEqual((slots[0][1] - slots[0][0]).total_seconds(), 300)

    def test_complete_observed_month_can_pass_and_measured_downtime_can_fail(self):
        rows = self.observations()
        good = summarize(rows, self.month, interval_seconds=300, now=self.after_month)
        self.assertEqual(good["status"], "pass")
        self.assertEqual(good["coverage_percent"], 100)
        for row in rows[:30]:
            row["status"] = "down"
        bad = summarize(rows, self.month, interval_seconds=300, now=self.after_month)
        self.assertEqual(bad["status"], "fail")
        self.assertLess(bad["observed_availability_percent"], 99)

    def test_missing_samples_are_unknown_even_when_observed_samples_are_all_up(self):
        result = summarize(self.observations()[:10], self.month, interval_seconds=300, now=self.after_month)
        self.assertEqual(result["status"], "pending")
        self.assertEqual(result["observed_availability_percent"], 100)
        self.assertGreater(result["unobserved_seconds"], 0)
        self.assertFalse(result["fully_observed_month"])

    def test_unfinished_month_and_future_samples_cannot_produce_pass(self):
        result = summarize(
            self.observations(),
            self.month,
            interval_seconds=300,
            now=datetime(2026, 2, 10, tzinfo=UTC),
        )
        self.assertEqual(result["status"], "pending")
        self.assertGreater(result["ignored_future_samples"], 0)

    def test_duplicate_probe_failure_wins_without_double_counting(self):
        rows = self.observations()
        rows.append(rows[0] | {"status": "down"})
        result = summarize(rows, self.month, interval_seconds=300, now=self.after_month)
        self.assertEqual(result["observed_down_seconds"], 300)
        self.assertEqual(result["coverage_percent"], 100)

    def test_only_preannounced_maintenance_is_excluded_without_overlap_double_counting(self):
        rows = self.observations()
        first = datetime.fromisoformat(rows[0]["observed_at"])
        maintenance = [
            {
                "start": first.isoformat(),
                "end": (first + timedelta(minutes=10)).isoformat(),
                "announced_at": (first - timedelta(days=1)).isoformat(),
                "reason": "Approved maintenance",
            }
        ]
        result = summarize(
            rows, self.month, interval_seconds=300, now=self.after_month, maintenance=maintenance * 2
        )
        self.assertEqual(result["announced_maintenance_seconds"], 600)
        maintenance[0]["announced_at"] = (first + timedelta(minutes=1)).isoformat()
        with self.assertRaises(ValueError):
            summarize(rows, self.month, interval_seconds=300, now=self.after_month, maintenance=maintenance)

    def test_invalid_timestamps_status_and_probe_credentials_are_rejected(self):
        for row in (
            {"observed_at": "2026-02-02T08:00:00", "status": "up"},
            {"observed_at": "2026-02-02T08:00:00+05:30", "status": "unknown"},
        ):
            with self.subTest(row=row), self.assertRaises(ValueError):
                summarize([row], self.month, now=self.after_month)
        with self.assertRaises(ValueError):
            probe("https://user:password@example.invalid/health/")


@override_settings(OTP_REQUIRED=True)
class ReadinessTests(TestCase):
    def test_public_readiness_checks_database_without_private_details(self):
        response = self.client.get(reverse("health"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})
        self.assertIn("no-store", response["Cache-Control"])

    def test_database_or_maintenance_outage_returns_generic_503(self):
        for error in (OperationalError("private database path"), BackupBusy("private lock")):
            with (
                self.subTest(error=type(error).__name__),
                patch("config.health.database_lock", side_effect=error),
            ):
                response = self.client.get(reverse("health"))
                self.assertEqual(response.status_code, 503)
                self.assertEqual(response.json(), {"status": "unavailable"})
                self.assertNotContains(response, "private", status_code=503)

    def test_readiness_is_public_even_during_otp_or_forced_password_change(self):
        user = User.objects.create_user(username="HEALTH_TEST", role=Role.STUDENT, must_change_password=True)
        self.client.force_login(user)
        self.assertEqual(self.client.get(reverse("health")).status_code, 200)
        self.assertEqual(self.client.post(reverse("health")).status_code, 405)

    def test_readiness_never_loads_authenticated_cookie_from_an_unavailable_database(self):
        user = User.objects.create_user(username="HEALTH_COOKIE", role=Role.STUDENT)
        self.client.force_login(user)
        with patch("django.contrib.sessions.backends.db.SessionStore.load", side_effect=OperationalError):
            self.assertEqual(self.client.get(reverse("health")).status_code, 200)
            with patch("config.health.database_lock", side_effect=OperationalError):
                self.assertEqual(self.client.get(reverse("health")).status_code, 503)
