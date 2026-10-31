# BL-29 / BL-30 readiness and retest evidence

Date: 31 October 2026. Application code: `18a9324`; browser-runner correction and complete pipeline:
`42f0746`. Later evidence/documentation commits do not change the measured application source.

## Verified fixes

The shared template contained literal Markdown fences before its doctype. The corrected template
renders in standards mode. Bootstrap 5.3.3 and its MIT license are now local assets; a blocked CDN
cannot remove the application's styling. `STATIC_ROOT` supports deployment asset collection.

Long identities wrap within navigation. Narrow-screen tables preserve readable headers and cells,
scroll inside their own region, and have an accessible name, keyboard focus and arrow-key access.
The initial visual review caught a Roll number heading compressed into a vertical column even though
the page-width assertion passed. A header-readability assertion now prevents that false pass.
WebKit's mobile case also exposed missing arrow-key scrolling; the table enhancement fixes it.

Tracked defect: [#54](https://github.com/Harsha-Kamaraj/Student-Attendance-Management-System/issues/54).
See [before](evidence/readiness/before-mobile-table.png) and
[after](evidence/readiness/after-mobile-table.png), plus the checked
[long-identity navigation](evidence/readiness/mobile-admin.png),
[student summary](evidence/readiness/mobile-student.png) and
[native Windows Edge](evidence/readiness/windows-edge-mobile.png) screenshots.

## Complete GitHub verification

[Run 41167521444](https://github.com/Harsha-Kamaraj/Student-Attendance-Management-System/actions/runs/41167521444)
completed with **all four jobs successful**:

| Job | Actual result |
| --- | --- |
| Ubuntu regression and capacity/performance | 477 discovered: **474 passed, 3 Windows-only skips**, no failures/errors; PT_01–PT_04 passed |
| Windows regression and capacity/performance | **477 passed, zero skips/failures/errors**; native ACL/junction/storage tests and PT_01–PT_04 passed |
| Ubuntu browser engines | Six cases at 1440px/360px, all passed |
| Installed Windows Chrome and Edge | Four cases at 1440px/360px, all passed |

Both regression jobs use the application's default password hashers. Real TOTP setup/login, security
boundaries, corrections, report/notification consistency, atomic recovery and readiness failures are
covered by the existing suites. The added doctype regression passes on both platforms.
The local targeted run also passed all 20 document/performance-evidence/availability checks.

An earlier mixed run had passing backend jobs but failures in browser layout measurement before
page/stylesheet loading settled. The runner now waits for load and loaded styling, retains the same
layout assertions, and records safe failure messages. The complete corrected run above is the final
acceptance evidence; a partially failing workflow is not counted as a passing complete run.

## BL-29: representative capacity and response targets

Targets and full sampling were frozen before each seed. Every run starts with 1,000 students,
60 faculty and 750,000 attendance records. The unchanged BL29-v1 workload uses 50 distinct authenticated
OTP-verified sessions, CSRF, 30 synchronized common-request rounds and three marking/export repetitions.

| Metric | Mac | Ubuntu CI | Windows CI | Target |
| --- | --- | --- | --- | --- |
| Common p95 | 0.186 s | 0.873 s | 1.283 s | At least 95% within 2 s |
| Common requests within 2 s | 1,500/1,500 | 1,500/1,500 | 1,500/1,500 | At least 95% |
| Slowest 60-student save | 0.328 s | 1.238 s | 1.789 s | Each at most 3 s |
| Slowest semester CSV | 0.193 s | 1.028 s | 1.254 s | Each at most 10 s |
| Successful measured requests | 1,800/1,800 | 1,800/1,800 | 1,800/1,800 | No functional failures |

Each run verifies 60 first-crossing in-app notifications and captured emails, no duplicate notifications
on later submissions, exactly 180 added marks, and correct semester-export scope/counts.

| Environment | Recorded configuration |
| --- | --- |
| Mac | macOS arm64; 10 logical CPUs; Python 3.14.6; PostgreSQL 18.4 |
| Ubuntu CI | Linux x86_64; 4 logical CPUs; Python 3.14.9; PostgreSQL 18.6 |
| Windows CI | Windows Server 2025; 4 logical CPUs; Python 3.13.17; PostgreSQL 17.11 |

The benchmark measures one process with 50 threads, loopback PostgreSQL, the complete in-process Django
request stack and normal commit callbacks with captured mail. It excludes the deployment network/proxy,
browser assets and external SMTP. The selected Windows CI profile is an explicit representative retest;
it is not a reproduction of the original Windows 11/PostgreSQL 16.15 machine in #49. All original targets
are retained. Review #49 against this declared profile; deployment performance still needs its own run.

The source fingerprint now includes static assets as well as application code/templates. Every result
retains source/plan/seed binding and the harness hashes. Per-request outcomes and actual configuration
are retained for [Mac](evidence/readiness/mac-performance.json),
[Ubuntu](evidence/readiness/linux-performance.json) and
[Windows](evidence/readiness/windows-performance.json).

## BL-30: executed browser matrix

| Host | Browser / engine | Widths | Result |
| --- | --- | --- | --- |
| Mac | Installed Chrome 156.0.8078.74 | 1440px, 360px | Passed |
| Mac | Playwright Chromium 156.0.8078.4 | 1440px, 360px | Passed |
| Mac | Playwright Firefox 157.0 | 1440px, 360px | Passed |
| Mac | Playwright WebKit 27.2 | 1440px, 360px | Passed |
| Ubuntu | Playwright Chromium 156.0.8078.4 | 1440px, 360px | Passed |
| Ubuntu | Playwright Firefox 157.0 | 1440px, 360px | Passed |
| Ubuntu | Playwright WebKit 27.2 | 1440px, 360px | Passed |
| Windows | Installed Chrome 156.0.8078.48 | 1440px, 360px | Passed |
| Windows | Installed Edge 155.0.4283.62 | 1440px, 360px | Passed |

This is **18 cases / 54 role journeys / 342 layout checkpoints**. Every case exercises Admin, Faculty
and Student with actual password/TOTP, validation messages, saved attendance and corrections, empty
states and logout. The 360px cases also execute keyboard scrolling. No uncaught JavaScript errors were
recorded. The browsers make real local HTTP requests with all external requests blocked.

The 360px cases emulate viewport/touch behavior; they are not physical Android/iOS tests. Playwright
WebKit is not branded Safari. Native Safari, previous branded browser releases and real Android/iOS
devices remain separate acceptance checks under the unchanged latest-two-version/device requirement.

Retained outcomes: [Mac](evidence/readiness/mac-browser.json),
[Ubuntu](evidence/readiness/linux-browser.json),
[native Windows browsers](evidence/readiness/windows-browser.json).
Full synthetic screenshots remain in the linked GitHub artifacts; representative screenshots are kept
in Git alongside the JSON so the core evidence survives artifact expiry.

## Deployment and remaining acceptance

Code fixes, repeatable tests, the checked browser matrix and the representative performance profiles
are ready for review. No application deployment exists yet, so a measured monthly 99% institutional-hours
availability result cannot be produced from these runs. The availability collector and its gap/future/
maintenance arithmetic are tested; missing deployment observations remain unknown.

After deployment, collect health observations every minute during the agreed 08:00–18:00 IST Monday–Saturday
window, then summarize a complete observed month. Repeat the capacity workload on the intended deployment
to include its actual server configuration. Run the remaining native browser/version/device checks before
claiming the full BL-30 matrix. These are explicit acceptance limits, not passing observations.

Run commands and deployment asset collection are in [verification/README.md](../../verification/README.md).
The [manifest](evidence/readiness/manifest.json) records original and retained evidence hashes and verifies
that JSON compaction preserved all measured values. All accounts, email addresses and screenshots are
synthetic; all fixture databases are disposable and separate from the development database.
