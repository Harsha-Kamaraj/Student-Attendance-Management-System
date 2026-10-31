"""BL-29: measured health probes and honest monthly business-hours availability.

Run ``python -m verification.availability --help``. This does not install a scheduler.
Missing samples remain unknown, and an unfinished/unobserved month cannot pass.
"""

import argparse
import json
import math
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

IST = ZoneInfo("Asia/Kolkata")
TARGET_PERCENT = 99


def _aware(value):
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("Timestamps must contain a timezone offset.")
    return parsed.astimezone(UTC)


def business_slots(month, interval_seconds=60):
    if type(interval_seconds) is not int or not 1 <= interval_seconds <= 300:
        raise ValueError("The probe interval must be 1–300 whole seconds.")
    start = datetime.strptime(month, "%Y-%m").replace(tzinfo=IST)
    if start.strftime("%Y-%m") != month:
        raise ValueError("Use YYYY-MM for the reporting month.")
    end = (start.replace(day=28) + timedelta(days=4)).replace(day=1)
    day = start
    slots = []
    while day < end:
        if day.weekday() < 6:
            moment, stop = day.replace(hour=8), day.replace(hour=18)
            while moment < stop:
                next_moment = min(moment + timedelta(seconds=interval_seconds), stop)
                slots.append((moment.astimezone(UTC), next_moment.astimezone(UTC)))
                moment = next_moment
        day += timedelta(days=1)
    return slots, end.astimezone(UTC)


def _maintenance_windows(entries):
    periods = []
    for entry in entries:
        start, end = _aware(entry["start"]), _aware(entry["end"])
        if end <= start or _aware(entry["announced_at"]) > start or not entry["reason"].strip():
            raise ValueError("Maintenance requires a valid interval and a reason announced before it starts.")
        periods.append((start, end))
    merged = []
    for start, end in sorted(periods):
        if merged and start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(end, merged[-1][1]))
        else:
            merged.append((start, end))
    return merged


def summarize(samples, month, *, interval_seconds=60, maintenance=(), now=None):
    """One scheduled slot per interval; duplicate failures win, gaps stay unknown."""
    now = now or datetime.now(UTC)
    if now.tzinfo is None:
        raise ValueError("The report time must contain a timezone offset.")
    slots, month_end = business_slots(month, interval_seconds)
    windows = _maintenance_windows(maintenance)
    observations = {}
    future_samples = 0
    for sample in samples:
        at = _aware(sample["observed_at"])
        status = sample["status"]
        if status not in {"up", "down"}:
            raise ValueError("Each observed status must be up or down.")
        if at > now:
            future_samples += 1
            continue
        local = at.astimezone(IST)
        if local.strftime("%Y-%m") != month or local.weekday() == 6 or not 8 <= local.hour < 18:
            continue
        offset = int((local - local.replace(hour=8, minute=0, second=0, microsecond=0)).total_seconds())
        slot = (
            local.replace(hour=8, minute=0, second=0, microsecond=0)
            + timedelta(seconds=offset // interval_seconds * interval_seconds)
        ).astimezone(UTC)
        if observations.get(slot) != "down":
            observations[slot] = status
    eligible = up = down = excluded = 0.0
    for start, end in slots:
        duration = (end - start).total_seconds()
        removed = sum(max(0, (min(end, b) - max(start, a)).total_seconds()) for a, b in windows)
        seconds = duration - removed
        eligible += seconds
        excluded += removed
        # A sample cannot certify the future remainder of its interval.
        if end > now:
            continue
        if observations.get(start) == "up":
            up += seconds
        elif observations.get(start) == "down":
            down += seconds
    observed = up + down
    complete = eligible > 0 and now >= month_end and math.isclose(observed, eligible) and not future_samples
    availability = round(100 * up / observed, 6) if observed else None
    return {
        "month": month,
        "timezone": "Asia/Kolkata",
        "business_hours": "08:00–18:00 Monday–Saturday",
        "target_percent": TARGET_PERCENT,
        "interval_seconds": interval_seconds,
        "eligible_seconds": eligible,
        "announced_maintenance_seconds": excluded,
        "observed_up_seconds": up,
        "observed_down_seconds": down,
        "unobserved_seconds": max(0, eligible - observed),
        "coverage_percent": round(100 * observed / eligible, 6) if eligible else 0,
        "observed_availability_percent": availability,
        "fully_observed_month": complete,
        "ignored_future_samples": future_samples,
        "status": ("pass" if up * 100 >= TARGET_PERCENT * eligible else "fail") if complete else "pending",
        "measured_at": now.astimezone(UTC).isoformat(),
        "method": "Scheduled-slot sampling; gaps are unknown, never assumed uptime.",
    }


def probe(url, *, timeout=3):
    parts = urlsplit(url)
    if parts.scheme not in {"http", "https"} or not parts.netloc or parts.username or parts.password:
        raise ValueError("Use an HTTP(S) health URL without credentials.")
    if parts.query or parts.fragment or timeout <= 0:
        raise ValueError("Health URLs must not contain query strings/fragments; timeout must be positive.")
    started = time.perf_counter()
    result = {"observed_at": datetime.now(UTC).isoformat(), "url": url, "status": "down"}
    try:
        with urlopen(
            Request(url, headers={"User-Agent": "Attendance-Availability-Probe/1"}), timeout=timeout
        ) as response:
            payload = json.loads(response.read(4096))
            if response.status == 200 and payload == {"status": "ok"}:
                result["status"] = "up"
            result["http_status"] = response.status
    except HTTPError as error:
        result["http_status"] = error.code
    except (URLError, TimeoutError, OSError, ValueError):
        result["error"] = "Health request failed or returned an invalid readiness response."
    result["elapsed_ms"] = round(1000 * (time.perf_counter() - started), 3)
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    observe = commands.add_parser("probe")
    observe.add_argument("--url", required=True)
    observe.add_argument("--log", type=Path, required=True)
    observe.add_argument("--timeout", type=float, default=3)
    report = commands.add_parser("summarize")
    report.add_argument("--log", type=Path, required=True)
    report.add_argument("--month", required=True)
    report.add_argument("--interval-seconds", type=int, default=60)
    report.add_argument("--maintenance", type=Path)
    report.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    if args.command == "probe":
        row = probe(args.url, timeout=args.timeout)
        args.log.parent.mkdir(parents=True, exist_ok=True)
        with args.log.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(row) + "\n")
        print(json.dumps(row))
        return 0 if row["status"] == "up" else 1
    samples = [json.loads(line) for line in args.log.read_text(encoding="utf-8").splitlines() if line.strip()]
    maintenance = json.loads(args.maintenance.read_text(encoding="utf-8")) if args.maintenance else []
    result = summarize(samples, args.month, interval_seconds=args.interval_seconds, maintenance=maintenance)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result))
    return 1 if result["status"] == "fail" else 0


if __name__ == "__main__":
    raise SystemExit(main())
