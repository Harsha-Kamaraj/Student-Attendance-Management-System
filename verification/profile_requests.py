"""Profile query counts on a fresh BL-29 fixture; never use this on application data.

This sequential diagnostic includes commit callbacks, but is not a load-test result.
SQL parameters, session cookies, passwords and message bodies are never recorded.
"""

import argparse
import re
import time
from collections import defaultdict
from datetime import date

from .performance import (
    VerificationError,
    check_seed_manifest,
    checked_plan,
    read_json,
    setup_django,
    source_revision,
    utc_now,
    write_json,
)
from .performance_data import actual_counts
from .performance_http import _prepare_personas, _request


def profile(plan, seed):
    from django.conf import settings
    from django.core import mail
    from django.db import connection

    from apps.academics.models import Enrollment, TeachingAssignment

    check_seed_manifest(plan, seed, settings.DATABASES["default"]["NAME"])
    counts = actual_counts()
    if any(
        counts[key] != plan["dataset"][key]
        for key in ("students", "faculty", "attendance_records", "sessions")
    ):
        raise VerificationError("Profiling requires a fresh, complete BL-29 seed.")
    personas = _prepare_personas()
    assignment = TeachingAssignment.objects.filter(faculty__faculty_id="BL29F000").order_by("pk").first()
    roster = list(Enrollment.objects.filter(assignment=assignment).values_list("student_id", flat=True))
    if len(roster) != 60:
        raise VerificationError("Expected the synthetic 60-student marking roster.")
    mail.get_connection()
    operations = [
        (personas[0], "dashboard_admin", None),
        (personas[1], "dashboard_faculty", None),
        (personas[-1], "dashboard_student", None),
        (personas[-1], "attendance_summary", None),
        (
            personas[1],
            "attendance_mark",
            {
                "assignment": assignment.pk,
                "date": date.fromisoformat(seed["benchmark_day"]).isoformat(),
                "period": 1,
                **{f"status_{pk}": "A" for pk in roster},
            },
        ),
    ]
    results = []
    for persona, route, payload in operations:
        queries = defaultdict(lambda: {"count": 0, "seconds": 0.0})

        def measure(execute, sql, params, many, context, queries=queries):
            # Retain only operation and table names, never literal SQL or parameters.
            table = re.search(r'(?:FROM|INTO|UPDATE)\s+"([a-z_]+)"', sql, re.IGNORECASE)
            key = sql.split()[0].upper() + (" " + table[1] if table else "")
            started = time.perf_counter()
            try:
                return execute(sql, params, many, context)
            finally:
                queries[key]["count"] += 1
                queries[key]["seconds"] += time.perf_counter() - started

        with connection.execute_wrapper(measure):
            sample, _ = _request(persona, route, "sequential_profile", time.perf_counter(), payload=payload)
        results.append(
            {
                "route": route,
                "ok": sample["ok"],
                "seconds": sample["seconds"],
                "query_count": sum(item["count"] for item in queries.values()),
                "queries": dict(queries),
            }
        )
    notifications = actual_counts()["notifications"] - counts["notifications"]
    return {
        "measured_at": utc_now(),
        "source_revision": source_revision(),
        "plan_id": plan["plan_id"],
        "boundary": "Sequential BL-29 diagnostic including commit callbacks; not load acceptance",
        "operations": results,
        "new_notifications": notifications,
        "locmem_emails": len(mail.outbox),
        "passed": all(item["ok"] for item in results) and notifications == 60 and len(mail.outbox) == 60,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", required=True)
    parser.add_argument("--seed", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    plan = checked_plan(args.plan)
    setup_django()
    from django.test import override_settings

    with override_settings(
        DEBUG=False,
        OTP_REQUIRED=True,
        ALLOWED_HOSTS=["testserver"],
        EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    ):
        result = profile(plan, read_json(args.seed))
    write_json(args.out, result)
    print(f"Profile retained: {args.out}; passed={result['passed']}")
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
