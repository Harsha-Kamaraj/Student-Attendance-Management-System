"""BL-29's measured Django request stack; real middleware, ORM and commit hooks."""

import csv
import hashlib
import io
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from pathlib import Path
from threading import Barrier

from .performance import (
    VerificationError,
    database_guard,
    environment_details,
    latency_statistics,
    source_revision,
    utc_now,
    write_json,
)
from .performance_data import actual_counts


def _prepare_personas():
    from django.test import Client

    from apps.accounts.models import User
    from apps.accounts.otp import SESSION_VERIFIED

    names = ["BL29ADMIN"] + [f"BL29F{i:03}" for i in range(10)] + [f"BL29S{i:04}" for i in range(39)]
    users = {user.username: user for user in User.objects.filter(username__in=names)}
    if len(users) != 50:
        raise VerificationError("The planned 50 distinct synthetic users do not exist.")
    personas = []
    for name in names:
        client = Client(enforce_csrf_checks=True, raise_request_exception=False)
        client.force_login(users[name])
        session = client.session
        session[SESSION_VERIFIED] = True
        session.save()
        personas.append({"client": client, "name": name, "role": users[name].role})
    return personas


def _route(persona, round_index):
    if persona["role"] == "ADMIN":
        return "dashboard_admin"
    if persona["role"] == "FACULTY":
        return "dashboard_faculty"
    return "dashboard_student" if round_index % 2 == 0 else "attendance_summary"


def _request(persona, route, phase, origin, *, payload=None, query=None):
    from django.urls import reverse

    client = persona["client"]
    path = reverse(route)
    started = time.perf_counter()
    error = None
    status = None
    body = b""
    location = ""
    try:
        if payload is None:
            response = client.get(path, query or {}, secure=True)
        else:
            csrf = client.cookies.get("csrftoken")
            response = client.post(
                path,
                payload,
                secure=True,
                HTTP_X_CSRFTOKEN=csrf.value if csrf else "",
                HTTP_ORIGIN="https://testserver",
            )
        body = b"".join(response.streaming_content) if response.streaming else response.content
        status = response.status_code
        location = response.get("Location", "")
    except Exception as exc:
        error = f"Request exception: {type(exc).__name__}"
    ended = time.perf_counter()
    expected = 302 if payload is not None else 200
    if error is None and status != expected:
        error = f"Expected HTTP {expected}, received {status}; redirect={location}"
    if error is None and payload is not None and not location.startswith(reverse("attendance_mark")):
        error = "Submission redirected outside the attendance workflow."
    if error is None and payload is None and route != "attendance_report_csv":
        if persona["name"].encode() not in body:
            error = "Authenticated identity is missing from the rendered response."
        elif persona["role"] == "STUDENT" and b"BL29S0999" in body:
            error = "Student response disclosed a different student's identity."
    return {
        "phase": phase,
        "route": route,
        "method": "POST" if payload is not None else "GET",
        "actor": persona["name"],
        "status": status,
        "seconds": ended - started,
        "started_offset": started - origin,
        "ended_offset": ended - origin,
        "ok": error is None,
        "error": error,
    }, body


def _wave(personas, round_index, phase, origin, *, foreground=None):
    from django.db import connections

    ready = Barrier(50)

    def worker(index, persona):
        try:
            ready.wait(timeout=120)
            if foreground is not None and index == foreground["index"]:
                return _request(
                    persona,
                    foreground["route"],
                    phase,
                    origin,
                    payload=foreground.get("payload"),
                    query=foreground.get("query"),
                )
            route = _route(persona, round_index)
            # Background traffic also exercises faculty history and report views.
            if foreground is not None and persona["role"] == "FACULTY":
                route = "attendance_history" if round_index % 2 == 0 else "attendance_report"
            return _request(persona, route, phase, origin)
        finally:
            connections.close_all()

    with ThreadPoolExecutor(max_workers=50) as pool:
        futures = [pool.submit(worker, index, persona) for index, persona in enumerate(personas)]
        return [future.result() for future in futures]


def _peak_inflight(samples):
    events = [(sample["started_offset"], 1) for sample in samples]
    events += [(sample["ended_offset"], -1) for sample in samples]
    active = peak = 0
    for _, delta in sorted(events):
        active += delta
        peak = max(peak, active)
    return peak


def _csv_check(body, expected_rolls):
    rows = list(csv.reader(io.StringIO(body.decode("utf-8-sig"))))
    if len(rows) != 301 or {row[0] for row in rows[1:]} != expected_rolls:
        return "Semester CSV did not contain exactly 300 authorized student/subject rows."
    if sum(int(row[6]) for row in rows[1:]) != 22500:
        return "Semester CSV totals did not summarize the expected 22,500 eligible marks."
    return None


def run_benchmark(plan, seed, *, output_path, phase="full"):
    from django.conf import settings
    from django.core import mail
    from django.db import connection

    from apps.academics.models import Enrollment, TeachingAssignment
    from apps.attendance.models import AttendanceSession

    database = database_guard(settings.DATABASES["default"])
    if seed.get("database_name") != database or seed.get("dataset") != plan["dataset"]:
        raise VerificationError("Seed manifest and declared dataset/database do not match.")
    baseline = actual_counts()
    for key in (
        "students",
        "faculty",
        "sections",
        "subjects",
        "assignments",
        "sessions",
        "attendance_records",
    ):
        if baseline[key] != plan["dataset"][key]:
            raise VerificationError(f"Run requires an untouched representative seed; {key} differs.")
    if settings.EMAIL_BACKEND != "django.core.mail.backends.locmem.EmailBackend":
        raise VerificationError("Only locmem mail is permitted in the synthetic benchmark.")
    mail.get_connection()  # Initializes the locmem outbox without delivering any external email.
    assignment = TeachingAssignment.objects.filter(faculty__faculty_id="BL29F000").order_by("pk").first()
    if assignment is None:
        raise VerificationError("Missing designated 60-student teaching assignment.")
    roster = list(Enrollment.objects.filter(assignment=assignment).values_list("student_id", flat=True))
    if len(roster) != 60:
        raise VerificationError("The marking workload needs exactly 60 enrolled students.")
    day = date.fromisoformat(seed["benchmark_day"])
    if AttendanceSession.objects.filter(assignment=assignment, date=day).exists():
        raise VerificationError("Submission slots are already occupied; use a fresh representative seed.")
    with connection.cursor() as cursor:
        cursor.execute("SELECT count(*) FROM accounts_user WHERE email NOT LIKE %s", ["%@attendance.invalid"])
        if cursor.fetchone()[0]:
            raise VerificationError("Unexpected non-synthetic email address in verification data.")
    origin = time.perf_counter()
    cpu_start = time.process_time()
    report = {
        "protocol": plan["protocol"],
        "plan_id": plan["plan_id"],
        "seed_plan_id": seed["seed_plan_id"],
        "declared_at": plan["declared_at"],
        "started_at": utc_now(),
        "source_revision": source_revision(),
        "dataset_id": seed["dataset_id"],
        "targets": plan["targets"],
        "sampling_plan": plan["workloads"],
        "baseline_counts": baseline,
        "environment": environment_details(),
        "samples": [],
        "selected_phase": phase,
        "harness_files_sha256": {
            name: hashlib.sha256(Path(__file__).with_name(name).read_bytes()).hexdigest()
            for name in (
                "performance.py",
                "performance_data.py",
                "performance_http.py",
                "performance_plan.json",
            )
        },
        "measurement_boundary": plan["measurement_boundary"],
        "availability": {
            "status": "pending_monthly_observation",
            "target": 0.99,
            "reason": "A local load run cannot establish monthly institutional-hours uptime.",
        },
    }
    progress_path = Path(str(output_path) + ".progress.json")

    def progress(phase):
        write_json(
            progress_path, {"phase": phase, "samples": len(report["samples"]), "at": utc_now()}, replace=True
        )
        print(f"BL-29 {phase}: {len(report['samples'])} measured requests", flush=True)

    personas = _prepare_personas()
    foreground_index = next(index for index, persona in enumerate(personas) if persona["name"] == "BL29F000")
    warmup = _wave(personas, 0, "warmup", origin)
    report["warmup"] = [sample for sample, _ in warmup]
    if any(not sample["ok"] for sample, _ in warmup):
        report.update(
            {"outcome": "failed", "finished_at": utc_now(), "failure": "Warmup/authentication failed"}
        )
        return report
    rounds = plan["workloads"]["common_requests"]["rounds"] if phase == "full" else 0
    for number in range(rounds):
        results = _wave(personas, number, "common", origin)
        report["samples"].extend(sample for sample, _ in results)
        if (number + 1) % 5 == 0:
            progress(f"common_round_{number + 1}")
    notification_events = []
    for number in range(plan["workloads"]["marking"]["repeats"]):
        before = actual_counts()["notifications"]
        emails_before = len(mail.outbox)
        payload = {
            "assignment": assignment.pk,
            "date": day.isoformat(),
            "period": number + 1,
            **{f"status_{student_id}": "A" for student_id in roster},
        }
        results = _wave(
            personas,
            number,
            "marking",
            origin,
            foreground={
                "index": foreground_index,
                "route": "attendance_mark",
                "payload": payload,
            },
        )
        event = {
            "repeat": number + 1,
            "new_notifications": actual_counts()["notifications"] - before,
            "locmem_emails": len(mail.outbox) - emails_before,
        }
        notification_events.append(event)
        sample = results[foreground_index][0]
        saved = AttendanceSession.objects.filter(assignment=assignment, date=day, period=number + 1).first()
        if saved is None or saved.records.count() != 60:
            sample.update({"ok": False, "error": "Submission did not persist exactly 60 marks."})
        if number == 0 and (event["new_notifications"] != 60 or event["locmem_emails"] != 60):
            sample.update(
                {"ok": False, "error": "First absence did not execute 60 notification/email callbacks."}
            )
        report["samples"].extend(result[0] for result in results)
        progress(f"marking_{number + 1}")
    report_repeats = plan["workloads"]["semester_report"]["repeats"] if phase == "full" else 0
    for number in range(report_repeats):
        results = _wave(
            personas,
            number,
            "semester_report",
            origin,
            foreground={
                "index": foreground_index,
                "route": "attendance_report_csv",
                "query": {
                    "start_date": seed["calendar"]["semester_start"],
                    "end_date": seed["calendar"]["semester_end"],
                },
            },
        )
        sample, body = results[foreground_index]
        if sample["ok"]:
            error = _csv_check(body, {f"BL29S{index:04}" for index in range(60)})
            if error:
                sample.update({"ok": False, "error": error})
        report["samples"].extend(result[0] for result in results)
        progress(f"semester_report_{number + 1}")
    samples = report["samples"]
    common = [sample for sample in samples if sample["phase"] == "common"]
    marks = [sample for sample in samples if sample["route"] == "attendance_mark"]
    semester = [sample for sample in samples if sample["route"] == "attendance_report_csv"]
    targets = plan["targets"]
    common_stats = latency_statistics(common, targets["common_requests_at_or_below_seconds"])
    mark_stats = latency_statistics(marks, targets["mark_60_students_max_seconds"])
    semester_stats = latency_statistics(semester, targets["semester_section_report_max_seconds"])
    after = actual_counts()
    expected_added = 60 * plan["workloads"]["marking"]["repeats"]
    checks = {
        "PT_01": (
            common_stats["within_limit_fraction"] >= 0.95 and common_stats["failed"] == 0 and rounds >= 30
        )
        if common
        else None,
        "PT_02": mark_stats["failed"] == 0 and mark_stats["within_limit_fraction"] == 1,
        "PT_03": (semester_stats["failed"] == 0 and semester_stats["within_limit_fraction"] == 1)
        if semester
        else None,
        "PT_04": (
            not any(not sample["ok"] for sample in samples)
            and after["attendance_records"] == baseline["attendance_records"] + expected_added
            and len(personas) == 50
        ),
    }
    ending_source = source_revision()
    report.update(
        {
            "finished_at": utc_now(),
            "final_counts": after,
            "checks": checks,
            "outcome": (
                "failed"
                if any(value is False for value in checks.values())
                else "partial_verification"
                if phase != "full"
                else "performance_passed_availability_pending"
            ),
            "latency": {"common": common_stats, "mark_60": mark_stats, "semester_report": semester_stats},
            "latency_by_route": {
                route: latency_statistics(
                    [sample for sample in samples if sample["route"] == route],
                    3 if route == "attendance_mark" else 10 if route == "attendance_report_csv" else 2,
                )
                for route in sorted({sample["route"] for sample in samples})
            },
            "offered_concurrent_authenticated_users": 50,
            "measured_peak_inflight_requests": _peak_inflight(samples),
            "notification_events": notification_events,
            "resources": {
                "python_process_cpu_seconds": time.process_time() - cpu_start,
                "wall_seconds": time.perf_counter() - origin,
            },
            "ending_source_revision": ending_source,
            "limitations": [
                "Network, proxy, external SMTP and browser asset latency excluded.",
                "Password/OTP setup excluded; persisted authenticated OTP-verified sessions used.",
                "Single Python process with 50 threads; not a production multiprocess deployment test.",
                "Availability remains pending a monthly institutional-hours observation window.",
            ],
        }
    )
    if ending_source != report["source_revision"]:
        report.update({"outcome": "failed", "failure": "Application source changed during the timed run."})
    return report
