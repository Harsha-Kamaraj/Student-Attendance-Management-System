# BL-29 and BL-31 verification

The benchmark, availability collector and integration tests support issues #29 and #31. Browser/device compatibility and usability in #30 remain a separate task.

## Regression and integration

Install `requirements-dev.txt`, configure a disposable PostgreSQL database, then run:

```bash
ruff check .
ruff format --check .
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test --noinput
```

To retain per-test outcomes and durations, set `VERIFICATION_RESULTS=artifacts/regression.json` and run `python manage.py test --noinput --testrunner verification.test_runner.Runner`. This opt-in runner extends the existing application runner and does not change application password hashing or OTP policy. Use shell-appropriate environment-variable syntax.

`tests.test_integration` exercises actual OTP setup and login, Admin provisioning and credential delivery, marking/correction, consistent dashboards and exports, alerts, role/CSRF denial, and encrypted backup/atomic recovery. All addresses are fictional; mail is captured locally and test backups use a new temporary key and private directory. Use application password hashers for security verification. The repository test runner preserves each test's explicit OTP requirement.

## Capacity and response times

Create an empty, disposable local PostgreSQL database named `verification_bl29_<suffix>`. Set `DATABASE_URL` to that database and `SECRET_KEY` to a verification-only value. The harness refuses a non-loopback host, an unrelated database name or populated application data.

```bash
python -m verification.performance plan --out artifacts/plan.json --rounds 30 --repeats 3
python manage.py migrate --noinput
python -m verification.performance seed --plan artifacts/plan.json --out artifacts/seed.json
python -m verification.performance run --plan artifacts/plan.json --seed artifacts/seed.json --out artifacts/performance.json
```

Declare the plan before seeding or measuring. A changed application revision requires a new plan and dataset. The seed contains 1,000 students, 60 faculty and 750,000 attendance records. The run uses 50 distinct persisted authenticated sessions, CSRF checks, 30 synchronized request rounds and three marking/report repetitions. Do not run other CPU-intensive checks during measurement.

At least 30 rounds **and three marking/report repetitions** are required for a full performance result.
Shorter runs are diagnostics, not acceptance evidence. The runner checks the declared workload and binds
the seed manifest to its plan, database and application revision.

To diagnose query overhead, create a separate fresh fixture using the plan/migrate/seed steps above, then run:

```bash
python -m verification.profile_requests --plan artifacts/plan.json --seed artifacts/seed.json --out artifacts/profile.json
```

This sequential profile records query counts by operation/table, without SQL parameters or credentials.
It includes a real 60-student submission and its 60 notification callbacks, so it consumes the fresh fixture.
Use a new empty database and seed for the concurrent benchmark; profile timings are not load-test results.

The measurement uses the in-process Django request stack and loopback PostgreSQL. OTP is enabled but the synthetic sessions have already passed OTP. Timings include middleware, queries, rendering and commit callbacks; mail is captured in memory. They exclude password/OTP setup, network/proxy delay, browser assets and an external SMTP provider. These results describe this local configuration; repeat the plan on the intended deployment before accepting deployment latency.

The manually dispatched **BL-29 and BL-31 verification** GitHub Actions workflow runs static checks, the complete suite and the same capacity benchmark on its isolated PostgreSQL service and uploads its JSON evidence. Defining the workflow does not mean a CI run has passed.

## Monthly availability

`GET /health/` returns generic no-cache JSON: HTTP 200 when the database is reachable and recovery is not holding maintenance, otherwise HTTP 503. It exposes no database errors or account information and does not load authenticated sessions.

Run the probe every minute from the monitoring location during institutional hours. The command writes one observation and exits; configure the scheduler separately.

```bash
python -m verification.availability probe --url https://your-attendance-host/health/ --log artifacts/availability.jsonl
python -m verification.availability summarize --log artifacts/availability.jsonl --month 2026-10 --output artifacts/availability-month.json
```

The agreed window is 08:00–18:00 Asia/Kolkata, Monday–Saturday, with a monthly 99% target. Missing slots remain unknown. A partial month, incomplete coverage or future observations cannot produce a pass. Duplicate failures win. Optional `--maintenance maintenance.json` accepts an array of objects containing timezone-aware `start`, `end`, `announced_at` and a nonempty `reason`; maintenance announced after its start is rejected. Keep the original announcement evidence with the monitoring records. A local smoke probe or recovery test cannot establish monthly availability.

See [the protocol](../Documents/Verification/BL-29_Protocol.md), [execution report](../Documents/Verification/BL-29-31_Results.md) and [defect retests](../Documents/Verification/BL-29-31_Defects.md).

The [30 October follow-up](../Documents/Verification/BL-29-31_Followup_2026-10-30.md) records the code
optimizations and local retest after PR #50. Deployment latency, the earlier Windows latency failure,
and monthly uptime must not be inferred from a passing Mac benchmark.
