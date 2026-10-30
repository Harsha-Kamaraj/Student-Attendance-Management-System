# BL-29 — Performance, capacity and availability protocol

Date: 29 October 2026. Requirement authority: BL-01 decision D-16; NFR-01, NFR-06 and NFR-08; performance test-plan rows PT_01–PT_04. This protocol records the agreed targets before measurement.

| Requirement | Target and acceptance method |
| --- | --- |
| Common requests | At least 95% of completed requests succeed within 2 seconds under 50 concurrent authenticated users. Failed responses do not count as within target. Record nearest-rank p50/p95/p99, maximum and errors. |
| Attendance submission | Each of three submissions for a 60-student roster completes within 3 seconds while 49 other users issue requests. Verify persisted marks and expected alerts. Include normal commit callbacks. |
| Semester section report | Each of three CSV exports completes within 10 seconds while 49 other users issue requests. Verify 300 student/subject rows representing 22,500 marks. |
| Capacity | Seed and count at least 1,000 students, 60 faculty and 750,000 saved attendance records across 250 teaching days; retain actual counts. |
| Availability | At least 99% over a complete month of 08:00–18:00 Monday–Saturday in Asia/Kolkata, excluding documented maintenance announced before it starts. Retain the original time-stamped observations and report coverage. |

## Frozen run and data

The plan command freezes targets, workloads, declaration time, a unique plan ID, base commit, application diff hash and application tree hash. The seeder refuses populated application data and records its plan ID and actual counts. Measurement refuses a different application revision or mismatched seed. The JSON plan and seed are retained under `evidence/`; the result file records the environment and every timed sample.

The representative fixture has 17 sections (16 of 60 students and one of 40), five subjects, 85 teaching assignments, 12,750 sessions and exactly 750 saved marks per student. Dates cover 250 Monday–Saturday teaching days strictly before the benchmark day. Attendance varies between fully present, zero present and either side of the 75% threshold. The marking roster starts at 113/150 so the first measured absence generates the subject's shortage notifications. All identities and addresses are fictional. Verification captures email locally and does not use institutional accounts, real student records or production backups.

## Workload and boundary

The common workload contains one Admin, ten Faculty and 39 Students. Each has a distinct persisted session. After one warm-up request per user, 50 workers synchronize before each of 30 timed rounds. Routes include all role dashboards and the student's attendance summary. The marking and reporting phases add one foreground operation to 49 background users and repeat three times.

The boundary is Django's in-process Client, using the complete middleware/request stack against local PostgreSQL, with CSRF enforcement and OTP enabled. Each wave creates 50 thread-pool workers and closes their Django connections at the end, so timings include ORM connection establishment and the single-process Python runtime. Synthetic sessions are prepared after the OTP gate for measurement. Request timing includes ORM queries, rendering and attendance commit callbacks. Email goes to the in-memory backend. Password/OTP enrollment, network and proxy latency, static assets, browser rendering and external mail transport are outside the measurement. This does not measure a production process pool or connection pool. Record this boundary with the result; deployment acceptance requires a representative run on the intended server.

Use an otherwise idle machine for timed phases. Preserve unsuccessful samples and errors. If a target fails, keep that result, link a defect, and measure a new frozen revision after remediation. Do not change targets to turn a failed result into a pass.

## Availability and recovery

The collector records one HTTP observation of the public `/health/` endpoint. A success requires HTTP 200 and the expected JSON status. Database failure and maintenance produce generic HTTP 503. Configure a one-minute schedule separately; the command itself does not install one. Summarization counts only the agreed institutional windows, keeps missing observations unknown, ignores future samples and lets a duplicate failure override a duplicate success. Only a complete, fully observed month can pass. Exclusions need a reason, start/end and an announcement time no later than the start.

Encrypted backup recovery, corrupt-artifact rejection, invalid-relationship rollback, session revocation and health failure behavior are verified separately under BL-31. They show tested recovery behavior and do not replace monthly uptime evidence.
