# BL-29 / BL-31 verification follow-up

This follow-up reviews merged PR #50 (`577489b`) and verifies the changes at `daebfc1`, including main `60cdba8` (PR #52).
The retained JSON records actual execution timestamps and source fingerprints. All records, accounts,
emails and backups used for verification are synthetic and isolated from `attendance_dev`.

## Code changes and defect retests

- **Dashboard calculations:** derive subject and pooled shortages from one grouped attendance query.
  This removes a second scan and keeps both metrics on the same database snapshot. Counts remain live;
  faculty scope, exact threshold comparisons and unequal subject weights are preserved.
- **Attendance notifications:** insert a threshold-crossing batch together and reload committed
  recipients once. Each student still receives an individual email after the attendance transaction
  commits. A failed recipient does not stop the others; rollback emits no email. A 60-student submission
  uses **30 queries instead of 148** in the retained sequential profiles. Notification insert/read
  queries drop from **120 to 2**; each staff dashboard uses **11 queries instead of 12**.
- **Report validation / [#51](https://github.com/Harsha-Kamaraj/Student-Attendance-Management-System/issues/51):**
  UT_09_2 in the refined test plan required a report scope and date range, but `main` generated
  unfiltered downloads. HTML, CSV and PDF now require both dates and an explicit scope. The initial
  page only shows the filter form. Users can choose a student, class-and-subject, class/section, or
  explicitly select all their authorized classes. Invalid/empty input produces no download or export
  audit event. Section selection cannot reveal another teacher's subjects in the same section.
- **Evidence guards:** shortened runs cannot claim full acceptance; at least 30 rounds and three
  marking/report repetitions are needed. Altered workloads and seed manifests from another plan,
  database or application revision are rejected. Targets were not weakened.

The report-query changes in the benchmark supply the now-required explicit scope/date parameters.
Background report requests still include all of the faculty member's authorized records across the
whole seeded calendar through the benchmark day. The foreground semester export selects F000's section,
which contains exactly the same five assignments, 300 student/subject rows and 22,500 marks as before.
These changes do not reduce the measured dataset or replace generated reports with an empty landing page.

## Local performance results

Environment: macOS arm64, 10 logical CPUs, Python 3.14.6, Django 5.2.18, PostgreSQL 18.4;
128 MB shared buffers and 4 MB work memory. The complete frozen BL29-v1 workload uses one Python
process, 50 synchronized threads, real Django middleware, persisted OTP-verified sessions and CSRF.
Email callbacks run synchronously with the in-memory mail backend. No other verification workload
ran during the timed baseline or final benchmark.

| Check | Baseline `577489b` | Final `daebfc1` | Required target / result |
| --- | --- | --- | --- |
| Common requests within 2 s | 1,500/1,500 | 1,500/1,500 | At least 95%; passed |
| Common p95 | 0.220 s | 0.186 s | Below 2 s |
| Common maximum | 0.265 s | 0.212 s | Recorded |
| Slowest 60-student submission | 0.306 s | 0.286 s | Each of three at most 3 s; passed |
| Slowest semester export | 0.200 s | 0.156 s | Each of three at most 10 s; passed |
| Functional requests | 1,800/1,800 | 1,800/1,800 | No failures; passed |
| Peak in-flight requests | 50 | 50 | 50 authenticated users; passed |

The baseline already passes on this Mac. These measurements therefore **do not demonstrate that the
earlier Windows latency failure has been resolved**, nor do they establish deployment latency.
The query reduction is reproducible independently of host speed; small timing differences are not a
guaranteed speedup. The final run starts with 1,000 students, 60 faculty and 750,000 marks, ends with
750,180 marks in 12,753 sessions, and verifies 60 first-crossing notifications/emails with no duplicates
on the subsequent two submissions. All PT_01–PT_04 checks pass within the declared local boundary.

Evidence: [baseline](evidence/followup/baseline-performance.json),
[final plan](evidence/followup/final-plan.json), [final seed](evidence/followup/final-seed.json),
[final per-request outcomes](evidence/followup/final-performance.json),
[profile before](evidence/followup/profile-before.json), [profile after](evidence/followup/profile-after.json).
The profiles cover the query optimization at `5c956ae`; the final benchmark includes the report fix.
Profiles are sequential diagnostics, not concurrent acceptance timings.

### Independent GitHub verification

[Workflow run 41153839750](https://github.com/Harsha-Kamaraj/Student-Attendance-Management-System/actions/runs/41153839750)
**passed** on Ubuntu at `27b5329`, before the subsequent PR #52 navigation merge. It independently ran
the complete suite (**473 passed, 3 Windows-only skips**) and all four performance checks against
PostgreSQL 18.6, Python 3.14.9 and four logical CPUs. All 1,800 requests succeeded; common p95 was
**0.901 s**, the slowest marking submission **1.285 s**, and the slowest semester export **0.964 s**.
All 1,500 common requests met the two-second target. These remain in-process test-stack measurements,
not external HTTP/deployment or Windows measurements.

The downloaded [plan](evidence/followup/github-plan.json), [seed](evidence/followup/github-seed.json),
[per-request results](evidence/followup/github-performance.json) and
[per-test results](evidence/followup/github-tests.json) are retained locally so the evidence survives
GitHub artifact expiry. The integrated Mac run above includes the later navigation merge. The latest
standard CI checks are attached to [PR #53](https://github.com/Harsha-Kamaraj/Student-Attendance-Management-System/pull/53).

## Integration, security and regression

The final suite discovered **476 tests: 473 passed, 0 failures/errors, 3 skipped**, in **80.635 seconds**.
It used the application's default password hashers. The three skips require native Windows ACL/junction
APIs; the existing PR #50 evidence records their earlier Windows execution. No new Windows execution
is claimed here. Ruff lint/format, Django system checks, migration drift, dependency consistency and
diff whitespace checks all passed.

The retained [per-test outcomes](evidence/followup/regression.json) provide actual names, statuses and
durations. [Static checks](evidence/followup/static-checks.json) retain commands and exit codes.

| Refined test-plan area | Executed coverage |
| --- | --- |
| UC-01 / BL-33 / BL-34 | Real password and OTP setup/login, credential delivery, forced password change, replay/expiry, lockouts, recovery, reset/session revocation |
| UC-02–05 | Student/faculty/subject/section provisioning and edits, enrollment/assignment validation, scope denial, preservation and deletion policies |
| UC-06–07 | Complete marking, duplicate/partial/concurrent saves, exact calculations, correction-window boundaries, Admin override reasons and atomic audit |
| UC-08 / UC-12 | Own-student views, filters, zero-class states, pooled totals, role dashboards, logout and expired sessions |
| UC-09 / UC-11 | Explicit scope/dates, section authorization, report denominator consistency, private/audited/formula-safe exports, empty/invalid/unsupported downloads, history/search |
| UC-10 | Exact threshold boundaries, first crossing/recovery/recrossing, private batch delivery, rollback, transport failure and weekly faculty notifications |
| UC-13 | Genuine encrypted backup/restore, integrity rejection, rollback, preserved audit, session revocation, maintenance/concurrency gates and readiness failures |

Five new report methods cover the missing UT_09_2 behavior and section scope. Five query/batch regression
methods cover pooled counts, private delivery, current recipient addresses, deleted notifications,
per-recipient failure and rollback. Four additional evidence tests reject invalid workloads/manifests
and false full-sampling claims. Existing integration journeys now pass explicit report selections while
retaining their original data/authorization assertions.

The Word test plan's UT_06_4 uses rejection language for all duplicate submissions. BL-13 intentionally
supports an identical retry without creating records; a changed retry is rejected and directed to
correction. The existing submission-safety tests verify both behaviors. This report does not claim that
every literal manual script was performed in a browser; browser/device/usability acceptance remains #30.

## Availability and completion boundary

The owner confirmed that there is **no deployed system or existing uptime history**. A real local
`/health/` probe returned HTTP 200; [the monthly summary](evidence/followup/availability-month.json)
correctly remains **pending**, with **0% institutional-hours coverage**. The local probe occurred
outside the institutional window and cannot establish monthly uptime.

| Issue | Verified now | Still needed before full closure |
| --- | --- | --- |
| #29 | Frozen workload, representative capacity, all local performance checks, availability/recovery tooling and regression coverage | Intended/representative deployment test and a fully observed month meeting 99% availability |
| #31 | Updated code, scoped report fix and full local integration/security/regression evidence | Merge/review the follow-up and resolve agreed release-blocking performance acceptance; no blanket release approval is claimed |
| #49 | Profiled query costs, reduced database work, passing before/after Mac benchmarks | Retest the original Windows configuration or an agreed representative deployment; Mac success does not invalidate the earlier failure |
| #51 | Validation and authorization fix with passing regression tests | Merge the follow-up |

Use `verification/README.md` to repeat the benchmark on a fresh disposable database and to configure
real health monitoring after deployment. The target, measurement boundary and missing observations
must remain explicit. The [manifest](evidence/followup/manifest.json) records evidence hashes and
confirms that JSON compaction preserved every measured value.
