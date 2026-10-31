"""Protect evidence statistics and the disposable database boundary for BL-29."""

from copy import deepcopy
from datetime import date
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.test import SimpleTestCase

from verification.performance import (
    VerificationError,
    check_seed_manifest,
    checked_plan,
    database_guard,
    declare_plan,
    latency_statistics,
    percentile,
    teaching_days_before,
    write_json,
)


class PerformanceEvidenceTests(SimpleTestCase):
    def test_short_smoke_run_cannot_claim_full_sampling(self):
        with TemporaryDirectory() as folder:
            path = Path(folder) / "plan.json"
            plan = declare_plan(path, rounds=30, repeats=1)
            self.assertFalse(plan["full_sampling_plan"])
            self.assertEqual(checked_plan(path), plan)

    def test_altered_workload_and_false_completeness_are_rejected(self):
        with TemporaryDirectory() as folder:
            path = Path(folder) / "plan.json"
            plan = declare_plan(path)
            for field, value in (
                ("rounds", 0),
                ("rounds", True),
                ("routes", ["dashboard_student"]),
                ("users", {"student": 1}),
            ):
                changed = deepcopy(plan)
                changed["workloads"]["common_requests"][field] = value
                write_json(path, changed, replace=True)
                with self.subTest(field=field), self.assertRaises(VerificationError):
                    checked_plan(path)
            changed = deepcopy(plan)
            changed["workloads"]["marking"]["repeats"] = 1
            changed["workloads"]["semester_report"]["repeats"] = 1
            write_json(path, changed, replace=True)
            with self.assertRaises(VerificationError):
                checked_plan(path)

    def test_source_change_requires_a_new_plan(self):
        with TemporaryDirectory() as folder:
            path = Path(folder) / "plan.json"
            declare_plan(path)
            with patch("verification.performance.source_revision", return_value={"head": "different"}):
                with self.assertRaises(VerificationError):
                    checked_plan(path)

    def test_seed_from_another_plan_or_source_is_rejected(self):
        plan = {
            "dataset": {"students": 1000},
            "plan_id": "one",
            "source_revision": {"head": "abc"},
            "declared_at": "2026-10-30T10:00:00+00:00",
        }
        seed = {
            "database_name": "verification_bl29_fixture",
            "dataset": plan["dataset"],
            "seed_plan_id": plan["plan_id"],
            "source_revision": plan["source_revision"],
            "plan_declared_at": plan["declared_at"],
        }
        check_seed_manifest(plan, seed, seed["database_name"])
        for field in seed:
            with self.subTest(field=field), self.assertRaises(VerificationError):
                check_seed_manifest(plan, seed | {field: "wrong"}, seed["database_name"])

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
