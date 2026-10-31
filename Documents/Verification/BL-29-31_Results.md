# BL-29 / BL-31 — Execution record

This is the original PR #50 execution record. See the [follow-up](BL-29-31_Followup.md) for later
query optimizations, report-validation corrections and retests; the original observations below are retained.

Date: 29 October 2026. Scope: #29 performance/capacity/availability and #31 integration/security/regression. #30's browser-version/device/usability matrix remains assigned separately. Tests use fictional accounts and locally captured email.

## Capacity and performance

The retained plan was declared at `2026-10-29T08:59:28.227525+00:00` before the seed completed at `2026-10-29T09:00:40.001327+00:00`. Plan ID: `14d9fe18-b379-4f9e-a41f-48e2ed22bf68`. The measured working tree is based on commit `3ba25e33d7cbb3630bb8aa197a54d4acb85aa370`; the evidence also records the application content hash, so uncommitted fixes are identified.

| Check | Actual result | Status |
| --- | --- | --- |
| Representative capacity | 1,000 students; 60 faculty; 1,061 users; 17 sections; 85 assignments; 5,000 enrollments; 12,750 sessions; 750,000 attendance records | Passed seed count verification |
| Common requests, 50 users / 30 rounds | Corrected run C: 1,500/1,500 responses successful; 336/1,500 (22.4%) within 2 s; p95 3.702 s, maximum 4.257 s | Failed; tracked in [#49](https://github.com/Harsha-Kamaraj/Student-Attendance-Management-System/issues/49) |
| Three 60-student submissions with 49 background users | All three saved exactly 60 marks and returned the expected HTTP 302; durations 5.780 s, 4.815 s and 3.798 s | Functional checks passed; each missed the 3-s target; [#49](https://github.com/Harsha-Kamaraj/Student-Attendance-Management-System/issues/49) remains open |
| Three semester section exports with 49 background users | 3/3 successful, each within 10 s; maximum 2.998 s; all 300 rows and 22,500 scoped marks verified | Passed this local report workload |
| Concurrent functional consistency | 1,800/1,800 measured requests successful; peak 50 simultaneously in flight; final records 750,180 and sessions 12,753; first mark generated 60 notifications and 60 captured emails, later marks generated no duplicates | Passed PT_04 and callback/persistence checks |
| Monthly 99% availability | One real local HTTP probe succeeded at 19:01 Asia/Kolkata, outside institutional hours; October has 0% observed coverage and 972,000 eligible seconds remain unknown | Pending; no monthly uptime claim |

Seed environment: Windows 11 build 26200; Python 3.13.5; Django 5.2.18; PostgreSQL 16.15; eight logical CPUs; PostgreSQL shared buffers 128 MB, work memory 4 MB and maximum connections 100. Database size after seeding: 134,437,911 bytes. This is an isolated loopback verification database. Latency scope is the in-process Django request stack described in [the protocol](BL-29_Protocol.md), including locally captured email callbacks and excluding network/proxy/browser/external SMTP.

Evidence: [frozen plan](evidence/performance-plan-b.json), [verified seed](evidence/performance-seed-b.json), [initial run B summary](evidence/performance-run-b-summary.json) and [corrected full run C](evidence/performance-run-c.json). Both runs used the same unchanged application tree SHA-256 `0f30d2b030177e067ddbf0566931ba03467622daf45229a16e0d9a9db1563f40`. Run C also records the harness file hashes. Its 30 common rounds plus three marking/report repetitions took 162.128 s of wall time and 79.047 s of Python process CPU time. For review size, B omits its per-request array but retains all three failed marking samples and records the omitted count and original artifact hash. C retains all 1,800 samples, with only JSON whitespace reformatted. [The manifest](evidence/evidence-manifest.json) records the original byte hashes and verified JSON-value equality for C.

The [exact measured request harness](evidence/performance_http-measured.txt) is retained with SHA-256 `6c7dd3578d567e7a7b7e524c7df5503878bc36eae81f1a69177decf79a1af283`, matching run C. The final repository script differs only by Ruff line wrapping of the metadata loop; its parsed Python syntax tree was verified equal to the measured version. The other three recorded harness hashes match their repository files.

The retained initial run B completed at 18:54:49 Asia/Kolkata. It had 1,500 successful common responses, 34.6% within 2 s and p95 4.163 s, but all three marking POSTs returned 403 because the HTTPS harness omitted its Origin/Referer. Those marking samples are not valid application-performance evidence. Correcting the harness retained native CSRF enforcement and changed no application code, source fingerprint, seed data or acceptance target. The full corrected run C above establishes successful writes/callbacks while confirming both response-time misses. No performance pass is claimed.

## Integration and security

The new 15-method integration suite runs real OTP provisioning/login and genuine encrypted restore. The table maps the selected refined test-plan scenarios exercised by these added tests; it does not assert that every row in each group was executed by them. In the initial application-hasher run, 14 methods passed; the foreign Faculty report checks exposed three subtest failures in the remaining method. After correcting foreign-ID authorization, the complete affected method passed its targeted rerun. Thus all 15 added methods have passed, including the retest; this does not replace the final full-suite result recorded below.

| Refined test-plan group | Executed journey and checked outcome | Result |
| --- | --- | --- |
| IT_01_1–3, ST_01_6; IT_02_1; IT_03_1; BL-34 credential delivery | Admin UI creates Faculty/Student accounts; credential email contains a temporary password; OTP setup and forced password change are enforced; password-only sessions cannot reach protected reports or mutation endpoints | Passed integration methods |
| IT_05_1–2; IT_06_1–3; IT_07_1–3; IT_12_1–2 | Provision assignments, save marks and correct attendance; verify canonical record values, dashboards and audit history | Passed integration journey |
| IT_08_1–5; IT_09_1–3 | Student totals, dashboard, filtered HTML, CSV and PDF agree after correction; filters preserve denominator; exports are private, audited, nonempty and formula-safe | Passed integration methods |
| IT_10_1, IT_10_5–6; AR-13/14 | Threshold crossing sends once, recovery resets, recrossing sends again; mail failure keeps saved marks/in-app alerts; weekly Faculty mail is scoped and not repeated | Passed integration methods |
| IT_01_2; IT_06_2; IT_07_2; IT_08_2/4/5; IT_09_2 | Student cross-account/Admin/Faculty requests denied; Faculty foreign class reads, exports and corrections denied; real logged-in requests require CSRF | Passed, including foreign-ID retest |
| IT_13_1–3 | Encrypted backup restores deleted accounts, attendance, alerts and working login; corrupt artifacts rejected without changing live data; invalid snapshot relationships roll back all restored modules | Passed genuine recovery integration methods |
| Transaction consistency | Failed attendance audit rolls back saved marks and alert changes and sends no email | Passed integration method |
| Static, dependency and schema checks | Ruff lint and formatting, Django system checks, migration-drift check and `pip check` all exited 0 | Passed; [execution evidence](evidence/static-checks.json) |
| Full regression suite | 462 tests executed in 285.822 s: 461 passed, 0 failures/errors, 1 Windows symlink-privilege skip | Passed with documented platform skip; [per-test outcomes](evidence/regression.json) |
| Functional Chromium journey with actual OTP | Chromium 153.0.8010.12 / Node 22.18.0, 127.271 s: all five workflow checks passed and no JavaScript errors | Passed; [sanitized execution evidence](evidence/browser-integration.json); no compatibility matrix claim |

## Additional recovery and monitoring checks

The final full-suite run used a test-only PBKDF2-SHA256 hasher with one iteration, supplied by an external verification settings class to accelerate fixtures. This changes no application hashing configuration and is recorded in the evidence metadata. Its result verifies functional regression, not password-hash cost. Separately, all 15 new integration methods passed with application-default hashing across the initial run and targeted foreign-ID retest, and the live browser journey used application-default hashing. The single full-suite skip requires Windows Developer Mode or symlink privilege; the separate real-junction and native ACL tests all passed.

The live browser journey ran at 19:00:25–19:02:32 Asia/Kolkata. Admin, Faculty and Student each completed actual OTP setup and code login; the password-only gate remained enforced. It then saved attendance and checked the shortage notification, corrected marks and checked scoped CSV/PDF output, observed role and CSRF denials, created/restored an encrypted backup, verified all prior sessions were revoked, and completed a fresh TOTP login with restored 100% totals. The saved evidence contains only sanitized outcomes and version/timestamp information; fixture keys, OTP secrets, backup content and credential emails are excluded. This is one functional browser execution for #31, separate from #30's browser/device/usability matrix.

Four native Windows storage tests passed: private publication/readback with no replacement, rejection of a publicly readable file ACL, rejection of a publicly readable storage directory and refusal of a real junction. POSIX protections remain in place; Windows-specific tests check the native handle/DACL behavior rather than POSIX permission bits.

All seven monthly-availability and four readiness tests passed in the full suite. They cover institutional windows, Sundays, complete-month pass/fail arithmetic, unknown gaps, future observations, duplicate failures and preannounced maintenance, plus public access during OTP/forced password change, generic database/maintenance failure and avoiding authenticated-cookie session access during a database outage. The four benchmark-guard/statistics/calendar tests also passed.

The [actual local probe](evidence/availability-local.jsonl) received HTTP 200 with the expected healthy JSON on 29 October at 19:01 Asia/Kolkata. The [October summary](evidence/availability-month.json) correctly remains `pending`: the probe is outside 08:00–18:00 and supplies no institutional-window coverage. It establishes endpoint reachability at that moment, not monthly availability or production reachability.

See [the defect/retest record](BL-29-31_Defects.md). Release acceptance remains pending wherever this document says pending; an unobserved monthly SLA or unexecuted browser matrix is not inferred from passing local integration tests.
