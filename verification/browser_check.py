"""BL-30 browser journeys against a guarded, disposable PostgreSQL database.

Install requirements-browser.txt and Playwright's browsers first. Set explicit
DATABASE_URL/SECRET_KEY; use an empty local verification_bl29_* database.
Screenshots contain synthetic dashboard data only, never passwords or OTP keys.
"""

import argparse
import hashlib
import importlib.metadata
import json
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from pathlib import Path
from urllib.parse import urlencode, urlsplit

from .performance import VerificationError, setup_django, source_revision, utc_now, write_json


def create_fixture():
    from apps.academics.models import Enrollment, Subject, TeachingAssignment
    from apps.accounts.models import User
    from apps.attendance.models import AttendanceRecord
    from tests.support_integration import IntegrationSupport

    if User.objects.exists() or Enrollment.objects.exists() or AttendanceRecord.objects.exists():
        raise VerificationError("Browser verification requires an empty disposable database.")

    class Fixture(IntegrationSupport):
        pass

    Fixture.make_fixture()
    # Exercise long identities and words instead of testing only short labels.
    Fixture.admin.username = "BROWSERADMIN_" + "A" * 110
    Fixture.admin.save(update_fields=["username"])
    Fixture.students[0].full_name = "Synthetic student " + "with a long readable name " * 4
    Fixture.students[0].save(update_fields=["full_name"])
    Fixture.empty_assignment = TeachingAssignment.objects.create(
        section=Fixture.section,
        subject=Subject.objects.create(code="EMPTY101", name="No enrolled students"),
        faculty=Fixture.assignment.faculty,
    )
    return Fixture


def check_layout(page):
    facts = page.evaluate("""() => {
      const visible = e => e.getClientRects().length && getComputedStyle(e).visibility !== 'hidden';
      const inputs = [...document.querySelectorAll('input:not([type=hidden]),select,textarea')]
        .filter(visible);
      const unlabeled = inputs.filter(e => !e.getAttribute('aria-label') && !e.getAttribute('aria-labelledby')
        && !e.closest('label') && !(e.id && document.querySelector('label[for="'+CSS.escape(e.id)+'"]')));
      const controls = 'main button,main input:not([type=hidden]),main select,main textarea,nav button';
      const outside = [...document.querySelectorAll(controls)]
        .filter(visible).filter(e => !e.closest('.table-responsive')).filter(e => {
          const r=e.getBoundingClientRect(); return r.left < -1 || r.right > innerWidth + 1;
        });
      return {mode:document.compatMode,width:innerWidth,scroll_width:document.documentElement.scrollWidth,
        navbar_display:getComputedStyle(document.querySelector('.navbar')).display,
        unlabeled_controls:unlabeled.length,offscreen_controls:outside.length,
        literal_fences:document.body.innerText.includes('```')};
    }""")
    assert facts["mode"] == "CSS1Compat", "The doctype must enable standards mode."
    assert facts["navbar_display"] == "flex", "The local Bootstrap stylesheet must load."
    assert facts["scroll_width"] <= facts["width"] + 1, "The page overflows horizontally."
    assert facts["unlabeled_controls"] == 0, "A visible form control has no accessible label."
    assert facts["offscreen_controls"] == 0, "A form control extends outside the viewport."
    assert not facts["literal_fences"], "Markdown fences must not render in the page."
    return facts


def database_action(action):
    """Keep synchronous ORM work off Playwright's event-loop/greenlet thread."""
    from django.db import connections

    def perform():
        try:
            return action()
        finally:
            connections.close_all()

    with ThreadPoolExecutor(max_workers=1) as pool:
        return pool.submit(perform).result()


def journey(browser, base, fixture, width, number, folder, *, mobile):
    import pyotp
    from django.utils import timezone
    from playwright.sync_api import expect

    from apps.accounts.models import User
    from apps.attendance.models import AttendanceRecord, AttendanceSession
    from tests.support_integration import PASSWORD

    result = {"width": width, "mobile_emulation": mobile, "steps": [], "page_errors": []}
    contexts = []
    current = {"stage": "prepare", "page": None}
    # New enrollment for each context exercises actual password + TOTP on every run.
    database_action(
        lambda: User.objects.all().update(
            otp_confirmed=False,
            otp_secret="",
            otp_last_step=None,
            otp_failed_count=0,
            otp_reset_token=uuid.uuid4(),
        )
    )
    day = timezone.localdate() - timedelta(days=number // 6)
    period = number % 6 + 1

    def checkpoint(page, label, *, screenshot=False):
        current.update(stage=label, page=page)
        facts = check_layout(page)
        item = {"name": label, "layout": facts}
        if screenshot:
            image_path = folder / f"{width}-{label}.png"
            page.screenshot(path=str(image_path), full_page=True)
            item["screenshot"] = image_path.name
        result["steps"].append(item)

    def signed_in(user, role):
        current["stage"] = role + "_login"
        options = {"viewport": {"width": width, "height": 900}, "has_touch": mobile}
        # Firefox does not implement Playwright's is_mobile mode. A narrow viewport
        # and touch input are still tested; the result never claims a real device.
        if mobile and browser.browser_type.name != "firefox":
            options["is_mobile"] = True
        context = browser.new_context(**options)
        contexts.append(context)
        page = context.new_page()
        current["page"] = page
        page.on("pageerror", lambda _: result["page_errors"].append("Uncaught JavaScript error"))

        def local_only(route):
            if urlsplit(route.request.url).hostname == "127.0.0.1":
                route.continue_()
            else:
                route.abort()

        page.route("**/*", local_only)
        page.goto(base + "/login/")
        page.get_by_role("button", name="Log in", exact=True).click()
        expect(page.get_by_text("This field is required.", exact=True)).to_have_count(2)
        checkpoint(page, role + "_required_fields")
        page.get_by_label("Username", exact=True).fill(user.username)
        page.get_by_label("Password", exact=True).fill(PASSWORD)
        page.get_by_role("button", name="Log in", exact=True).click()
        expect(page.get_by_role("heading", name="Set up two-factor login", exact=True)).to_be_visible()
        key = page.locator("code").inner_text().replace(" ", "")
        page.locator('input[name="code"]').fill(pyotp.TOTP(key).now())
        page.get_by_role("button", name="Confirm and continue").click()
        expect(page.get_by_test_id("backup-codes")).to_be_visible()
        page.goto(base + "/dashboard/")
        expect(page.get_by_role("heading", name=role.title() + " dashboard", exact=True)).to_be_visible()
        checkpoint(page, role + "_dashboard", screenshot=True)
        return page

    try:
        admin = signed_in(fixture.admin, "admin")
        admin.goto(base + "/students/")
        checkpoint(admin, "admin_student_table")
        admin.goto(base + "/students/create/")
        admin.get_by_role("button", name="Save", exact=True).click()
        assert admin.get_by_text("This field is required.", exact=True).count() >= 3
        checkpoint(admin, "admin_invalid_student")
        admin.goto(base + "/attendance/reports/")
        expect(admin.get_by_text("Choose a report scope and date range", exact=False)).to_be_visible()
        checkpoint(admin, "admin_report_form")
        future = (timezone.localdate() + timedelta(days=10)).isoformat()
        admin.locator('input[name="start_date"]').fill(future)
        admin.locator('input[name="end_date"]').fill(future)
        admin.locator('select[name="section"]').select_option(str(fixture.section.pk))
        admin.get_by_role("button", name="Generate report", exact=True).click()
        expect(
            admin.get_by_text("No attendance records match the selected filters.", exact=True)
        ).to_be_visible()
        expect(admin.get_by_role("link", name="Download CSV", exact=True)).to_have_count(0)
        checkpoint(admin, "admin_empty_report")

        faculty = signed_in(fixture.faculty_user, "faculty")
        faculty.goto(base + "/my-classes/")
        checkpoint(faculty, "faculty_classes")
        query = {"assignment": fixture.assignment.pk, "date": day.isoformat(), "period": period}
        faculty.goto(base + "/attendance/mark/?" + urlencode(query))
        faculty.get_by_role("radio", name="ITS001 Present", exact=True).check()
        faculty.get_by_role("button", name="Save complete attendance", exact=True).click()
        expect(faculty.get_by_text("Mark every enrolled student", exact=False)).to_be_visible()
        checkpoint(faculty, "faculty_incomplete_roster")
        faculty.get_by_role("button", name="Mark remaining as Present", exact=True).click()
        expect(faculty.get_by_role("radio", name="ITS001 Present", exact=True)).to_be_checked()
        expect(faculty.get_by_role("radio", name="ITS002 Present", exact=True)).to_be_checked()
        faculty.get_by_role("radio", name="ITS002 Absent", exact=True).check()
        faculty.get_by_role("button", name="Save complete attendance", exact=True).click()
        expect(faculty.get_by_text("This attendance session is already saved.", exact=False)).to_be_visible()
        checkpoint(faculty, "faculty_saved_roster", screenshot=True)

        def saved_record():
            session = AttendanceSession.objects.get(assignment=fixture.assignment, date=day, period=period)
            assert session.records.count() == 2
            return AttendanceRecord.objects.get(session=session, student=fixture.students[1])

        record = database_action(saved_record)
        assert record.status == "A"
        faculty.goto(base + f"/attendance/records/{record.pk}/correct/")
        faculty.get_by_label("Corrected status", exact=True).select_option("P")
        faculty.get_by_label("Reason", exact=True).fill("Synthetic browser verification correction")
        faculty.get_by_role("button", name="Save correction", exact=True).click()
        expect(faculty.get_by_role("heading", name="Attendance changes", exact=True)).to_be_visible()
        database_action(record.refresh_from_db)
        assert record.status == "P"
        checkpoint(faculty, "faculty_correction")
        faculty.goto(
            base + "/attendance/mark/?" + urlencode(query | {"assignment": fixture.empty_assignment.pk})
        )
        expect(faculty.get_by_text("This class has no active enrolled students.", exact=True)).to_be_visible()
        checkpoint(faculty, "faculty_empty_roster")

        student = signed_in(fixture.students[0].user, "student")
        student.goto(base + "/attendance/mine/")
        expect(student.get_by_text("100.00%", exact=False).first).to_be_visible()
        checkpoint(student, "student_summary", screenshot=True)
        student.locator('input[name="start_date"]').fill(future)
        student.locator('input[name="end_date"]').fill(day.isoformat())
        student.get_by_role("button", name="Apply", exact=True).click()
        expect(
            student.get_by_text("End date must be on or after the start date.", exact=True)
        ).to_be_visible()
        checkpoint(student, "student_invalid_dates")
        student.locator('input[name="end_date"]').fill(future)
        student.get_by_role("button", name="Apply", exact=True).click()
        expect(
            student.get_by_text("No attendance records match these filters.", exact=True).first
        ).to_be_visible()
        checkpoint(student, "student_empty_summary")
        student.goto(base + "/notifications/")
        expect(student.get_by_text("You have no notifications.", exact=True)).to_be_visible()
        checkpoint(student, "student_empty_notifications")
        for page in (admin, faculty, student):
            page.get_by_role("button", name="Log out", exact=True).click()
            expect(page.get_by_role("heading", name="Log in", exact=True)).to_be_visible()
        assert not result["page_errors"], "The journey had a JavaScript error."
        result["status"] = "passed"
    except Exception as error:
        result.update(status="failed", failed_stage=current["stage"], error_type=type(error).__name__)
        # OTP setup and backup-code pages must never be captured, even on failure.
        page = current["page"]
        if page and "/otp/" not in page.url and "/login/" not in page.url:
            page.screenshot(path=str(folder / f"{width}-failure.png"), full_page=True)
    finally:
        for context in contexts:
            context.close()
    return result


def run_matrix(engines, widths, output):
    from django.contrib.staticfiles.handlers import StaticFilesHandler
    from django.core.servers.basehttp import ThreadedWSGIServer, WSGIRequestHandler
    from django.core.wsgi import get_wsgi_application
    from django.db import connections
    from playwright.sync_api import sync_playwright

    class QuietHandler(WSGIRequestHandler):
        def log_message(self, *args):
            pass

    fixture = create_fixture()
    server = ThreadedWSGIServer(("127.0.0.1", 0), QuietHandler, allow_reuse_address=False)
    server.set_app(StaticFilesHandler(get_wsgi_application()))
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    base = f"http://127.0.0.1:{server.server_port}"
    result = {
        "started_at": utc_now(),
        "source_revision": source_revision(),
        "runner_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "playwright": importlib.metadata.version("playwright"),
        "cases": [],
        "boundary": (
            "Browser HTTP journeys against local threaded WSGI; synthetic data; OTP enabled; "
            "all external requests blocked"
        ),
    }
    number = 0
    try:
        with sync_playwright() as playwright:
            for engine in engines:
                kind = playwright.chromium if engine in ("chrome", "msedge") else getattr(playwright, engine)
                try:
                    browser = kind.launch(
                        headless=True, **({"channel": engine} if engine in ("chrome", "msedge") else {})
                    )
                except Exception as error:
                    result["cases"].extend(
                        {
                            "engine": engine,
                            "width": width,
                            "status": "failed",
                            "failed_stage": "browser_launch",
                            "error_type": type(error).__name__,
                        }
                        for width in widths
                    )
                    continue
                try:
                    for width in widths:
                        folder = output.parent / "screenshots" / engine
                        folder.mkdir(parents=True, exist_ok=True)
                        case = journey(browser, base, fixture, width, number, folder, mobile=width <= 360)
                        case.update(engine=engine, browser_version=browser.version)
                        result["cases"].append(case)
                        write_json(str(output) + ".progress.json", result, replace=True)
                        print(
                            f"{engine} {browser.version} {width}px: {case['status']} "
                            f"{case.get('failed_stage', '')}",
                            flush=True,
                        )
                        number += 1
                finally:
                    browser.close()
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=5)
        connections.close_all()
    ending = source_revision()
    result.update(
        finished_at=utc_now(),
        ending_source_revision=ending,
        passed=len(result["cases"]) == len(engines) * len(widths)
        and all(case["status"] == "passed" for case in result["cases"])
        and ending == result["source_revision"],
    )
    result["limitations"] = [
        "Viewport/touch emulation does not certify real Android/iOS devices.",
        "Playwright WebKit is not branded Safari; versions actually tested are recorded.",
        "Previous branded browser releases require separate runs; no two-version claim is inferred.",
    ]
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--engines",
        nargs="+",
        choices=["chromium", "firefox", "webkit", "chrome", "msedge"],
        default=["chromium", "firefox", "webkit"],
    )
    parser.add_argument("--widths", nargs="+", type=int, default=[1440, 360])
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if (
        args.out.exists()
        or any(width < 320 for width in args.widths)
        or len(args.engines) * len(args.widths) > 18
    ):
        raise VerificationError("Choose a new evidence file, widths >= 320px and at most 18 cases.")
    setup_django()
    from django.test import override_settings

    with override_settings(
        DEBUG=False,
        OTP_REQUIRED=True,
        ALLOWED_HOSTS=["127.0.0.1"],
        EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
        SESSION_COOKIE_SECURE=False,
        CSRF_COOKIE_SECURE=False,
    ):
        result = run_matrix(args.engines, args.widths, args.out)
    write_json(args.out, result)
    print(json.dumps({"passed": result["passed"], "cases": len(result["cases"])}))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
