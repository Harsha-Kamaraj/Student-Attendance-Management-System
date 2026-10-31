"""BL-29: declare a plan, seed an isolated database, then measure the request stack.

python -m verification.performance plan --out /path/to/plan.json
python -m verification.performance seed --plan /path/to/plan.json --out /path/to/seed.json
python -m verification.performance run --plan plan.json --seed seed.json --out run.json

Set DATABASE_URL and SECRET_KEY before seed/run. Only local PostgreSQL databases
named verification_bl29_* are accepted; populated application databases cannot be seeded.
"""

import argparse
import hashlib
import json
import math
import os
import platform
import re
import subprocess
import sys
import uuid
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLAN_TEMPLATE = Path(__file__).with_name("performance_plan.json")


class VerificationError(RuntimeError):
    """A safe, actionable verification failure."""


def utc_now():
    return datetime.now(UTC).isoformat()


def percentile(values, percent):
    """Nearest-rank percentile: p95 is the first value covering at least 95%."""
    if not values or not 0 <= percent <= 100:
        raise ValueError("Percentiles require samples and a percentage from 0 to 100.")
    ordered = sorted(values)
    if any(not math.isfinite(value) or value < 0 for value in ordered):
        raise ValueError("Latency samples must be finite nonnegative numbers.")
    return ordered[max(0, math.ceil(percent / 100 * len(ordered)) - 1)]


def latency_statistics(samples, limit):
    if not samples:
        return {"count": 0, "passed": False, "error": "No completed requests"}
    values = [sample["seconds"] for sample in samples]
    successes = [sample for sample in samples if sample["ok"]]
    within = sum(sample["ok"] and sample["seconds"] <= limit for sample in samples)
    return {
        "count": len(samples),
        "successful": len(successes),
        "failed": len(samples) - len(successes),
        "limit_seconds": limit,
        "within_limit": within,
        "within_limit_fraction": within / len(samples),
        "p50_seconds": percentile(values, 50),
        "p95_seconds": percentile(values, 95),
        "p99_seconds": percentile(values, 99),
        "max_seconds": max(values),
    }


def database_guard(config):
    """Validate configuration before opening or mutating a database connection."""
    if config.get("ENGINE") not in (
        "django.db.backends.postgresql",
        "django.db.backends.postgresql_psycopg2",
    ):
        raise VerificationError("BL-29 requires PostgreSQL.")
    name = str(config.get("NAME", ""))
    if not re.fullmatch(r"verification_bl29_[a-z0-9_]{1,40}", name):
        raise VerificationError("Use a disposable database named verification_bl29_*.")
    if str(config.get("HOST", "")) not in ("127.0.0.1", "localhost", "::1"):
        raise VerificationError(
            "This benchmark accepts only an explicitly configured loopback database host."
        )
    return name


def teaching_days_before(today, count=250):
    """Most recent institutional Mon–Sat dates, ending strictly before today."""
    if type(today) is not date or count < 1:
        raise ValueError("Supply a date and a positive teaching-day count.")
    days = []
    current = today - timedelta(days=1)
    while len(days) < count:
        if current.weekday() < 6:
            days.append(current)
        current -= timedelta(days=1)
    return list(reversed(days))


def source_revision():
    def git(*args):
        return subprocess.check_output(["git", *args], cwd=ROOT, stderr=subprocess.DEVNULL)

    try:
        head = git("rev-parse", "HEAD").decode().strip()
        diff = git("diff", "HEAD", "--", "apps", "config", "templates", "requirements.txt")
        files = git(
            "ls-files",
            "-z",
            "--cached",
            "--others",
            "--exclude-standard",
            "--",
            "apps",
            "config",
            "templates",
            "requirements.txt",
            "requirements-dev.txt",
        ).split(b"\0")
        tree = hashlib.sha256()
        for raw_path in sorted(set(files)):
            if not raw_path:
                continue
            relative = raw_path.decode("utf-8")
            path = ROOT / relative
            if path.is_file():
                tree.update(raw_path + b"\0" + path.read_bytes() + b"\0")
    except (OSError, subprocess.CalledProcessError):
        return {"head": "unavailable", "application_diff_sha256": "unavailable"}
    return {
        "head": head,
        "application_diff_sha256": hashlib.sha256(diff).hexdigest(),
        "application_tree_sha256": tree.hexdigest(),
    }


def read_json(path):
    with Path(path).open(encoding="utf-8") as source:
        return json.load(source)


def write_json(path, value, *, replace=False):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w" if replace else "x", encoding="utf-8") as target:
        json.dump(value, target, indent=2, ensure_ascii=False)
        target.write("\n")


def declare_plan(path, *, rounds=30, repeats=3):
    if type(rounds) is not int or rounds < 1 or type(repeats) is not int or not 1 <= repeats <= 6:
        raise VerificationError("Use at least one round and 1–6 marking/report repeats.")
    plan = read_json(PLAN_TEMPLATE)
    plan.update(
        {"plan_id": str(uuid.uuid4()), "declared_at": utc_now(), "source_revision": source_revision()}
    )
    plan["workloads"]["common_requests"]["rounds"] = rounds
    plan["workloads"]["marking"]["repeats"] = repeats
    plan["workloads"]["semester_report"]["repeats"] = repeats
    plan["full_sampling_plan"] = rounds >= 30 and repeats >= 3
    write_json(path, plan)
    return plan


def checked_plan(path):
    plan = read_json(path)
    template = read_json(PLAN_TEMPLATE)
    for field in ("protocol", "targets", "dataset"):
        if plan.get(field) != template[field]:
            raise VerificationError(f"Plan {field} must match the reviewed BL-29 protocol.")
    try:
        rounds = plan["workloads"]["common_requests"]["rounds"]
        repeats = plan["workloads"]["marking"]["repeats"]
    except (KeyError, TypeError) as error:
        raise VerificationError("Plan must retain the declared workloads.") from error
    if type(rounds) is not int or rounds < 1 or type(repeats) is not int or not 1 <= repeats <= 6:
        raise VerificationError("Use at least one round and 1–6 marking/report repeats.")
    expected = template["workloads"]
    expected["common_requests"]["rounds"] = rounds
    expected["marking"]["repeats"] = repeats
    expected["semester_report"]["repeats"] = repeats
    if plan["workloads"] != expected or plan.get("full_sampling_plan") != (rounds >= 30 and repeats >= 3):
        raise VerificationError("Workload or sampling completeness differs from the reviewed protocol.")
    if not plan.get("declared_at") or not plan.get("plan_id"):
        raise VerificationError("Create the dated plan with the plan command before loading or measuring.")
    if plan.get("source_revision") != source_revision():
        raise VerificationError(
            "Application revision changed: declare a new plan before measuring this revision."
        )
    return plan


def check_seed_manifest(plan, seed, database):
    if (
        seed.get("database_name") != database
        or seed.get("dataset") != plan["dataset"]
        or seed.get("seed_plan_id") != plan["plan_id"]
        or seed.get("source_revision") != plan["source_revision"]
        or seed.get("plan_declared_at") != plan["declared_at"]
    ):
        raise VerificationError("Seed manifest must match the declared plan, source revision and database.")


def setup_django():
    if not os.environ.get("DATABASE_URL") or not os.environ.get("SECRET_KEY"):
        raise VerificationError("Set explicit DATABASE_URL and a verification-only SECRET_KEY.")
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    import django

    django.setup()
    from django.conf import settings
    from django.db import connection

    name = database_guard(settings.DATABASES["default"])
    with connection.cursor() as cursor:
        cursor.execute("SELECT current_database()")
        if cursor.fetchone()[0] != name:
            raise VerificationError("Connected database does not match the guarded verification name.")


def environment_details():
    import django
    from django.conf import settings
    from django.db import connection

    with connection.cursor() as cursor:
        cursor.execute("SELECT version(), pg_database_size(current_database())")
        version, database_bytes = cursor.fetchone()
        postgres_settings = {}
        for setting in ("max_connections", "shared_buffers", "work_mem", "max_parallel_workers_per_gather"):
            cursor.execute("SELECT current_setting(%s)", [setting])
            postgres_settings[setting] = cursor.fetchone()[0]
    database = settings.DATABASES["default"]
    return {
        "python": sys.version.split()[0],
        "django": django.get_version(),
        "platform": platform.platform(),
        "logical_cpus": os.cpu_count(),
        "postgresql": version,
        "postgresql_settings": postgres_settings,
        "database": {key.lower(): str(database.get(key, "")) for key in ("HOST", "PORT", "NAME")},
        "database_bytes": database_bytes,
        "otp_required": True,
        "csrf_enforced": True,
        "mail_backend": "django.core.mail.backends.locmem.EmailBackend",
        "deployment": "one Python process, 50 threads, loopback PostgreSQL; in-process Django request stack",
    }


def cli(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    plan = commands.add_parser("plan", help="Freeze targets and sampling before seed/run")
    plan.add_argument("--out", required=True)
    plan.add_argument("--rounds", type=int, default=30)
    plan.add_argument("--repeats", type=int, default=3)
    for command in ("seed", "run"):
        sub = commands.add_parser(command)
        sub.add_argument("--plan", required=True)
        sub.add_argument("--out", required=True)
        if command == "run":
            sub.add_argument("--seed", required=True)
            sub.add_argument("--phase", choices=("full", "marking"), default="full")
    args = parser.parse_args(argv)
    try:
        if args.command == "plan":
            result = declare_plan(args.out, rounds=args.rounds, repeats=args.repeats)
            print(json.dumps({"plan_id": result["plan_id"], "path": str(args.out)}))
            return 0
        if Path(args.out).exists():
            raise VerificationError("Output already exists; choose a new evidence filename.")
        plan = checked_plan(args.plan)
        setup_django()
        from django.test import override_settings

        with override_settings(
            DEBUG=False,
            OTP_REQUIRED=True,
            ALLOWED_HOSTS=["testserver"],
            EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
            DEFAULT_FROM_EMAIL="verification@attendance.invalid",
            SITE_URL="https://attendance.invalid",
        ):
            if args.command == "seed":
                from .performance_data import seed_database

                result = seed_database(plan)
            else:
                from .performance_http import run_benchmark

                result = run_benchmark(plan, read_json(args.seed), output_path=args.out, phase=args.phase)
        write_json(args.out, result)
        print(json.dumps({"command": args.command, "path": str(args.out), "outcome": result.get("outcome")}))
        return 0 if result.get("outcome") != "failed" else 1
    except (VerificationError, FileExistsError, ValueError) as error:
        print(f"Verification refused: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(cli())
