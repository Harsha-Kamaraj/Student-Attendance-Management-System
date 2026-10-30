"""Protect evidence statistics and the disposable database boundary for BL-29."""

from datetime import date

from django.test import SimpleTestCase

from verification.performance import (
    VerificationError,
    database_guard,
    latency_statistics,
    percentile,
    teaching_days_before,
)


class PerformanceEvidenceTests(SimpleTestCase):
    def test_failed_requests_never_count_towards_response_time_target(self):
        samples = [{"seconds": 0.01, "ok": False}] + [{"seconds": 1.0, "ok": True} for _ in range(19)]
        result = latency_statistics(samples, 2)
        self.assertEqual(result["failed"], 1)
        self.assertEqual(result["within_limit_fraction"], 0.95)
        self.assertEqual(result["p95_seconds"], 1)

    def test_percentile_uses_upper_tail_and_rejects_invalid_samples(self):
        self.assertEqual(percentile([1] * 94 + [3] * 6, 95), 3)
        for values in ([], [-1], [float("nan")], [float("inf")]):
            with self.subTest(values=values), self.assertRaises(ValueError):
                percentile(values, 95)

    def test_database_guard_refuses_real_remote_and_non_postgres_databases(self):
        valid = {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": "verification_bl29_fixture",
            "HOST": "127.0.0.1",
        }
        self.assertEqual(database_guard(valid), valid["NAME"])
        for change in (
            {"NAME": "attendance"},
            {"NAME": "verification_bl29_fixture;DROP"},
            {"HOST": "database.example.com"},
            {"HOST": ""},
            {"ENGINE": "django.db.backends.sqlite3"},
        ):
            with self.subTest(change=change), self.assertRaises(VerificationError):
                database_guard({**valid, **change})

    def test_representative_calendar_has_250_mon_sat_days_in_one_year(self):
        today = date(2026, 10, 29)
        days = teaching_days_before(today)
        self.assertEqual(len(days), 250)
        self.assertEqual(len(set(days)), 250)
        self.assertTrue(all(day.weekday() < 6 and day < today for day in days))
        self.assertLess((today - days[0]).days, 366)
