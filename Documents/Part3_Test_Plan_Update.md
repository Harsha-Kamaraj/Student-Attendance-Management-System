# Part 3 test plan and case update

Date: 6 November 2026. Scope: testing of the completed implementation; no Sprint 3.

The earlier [Test Plan Document](Test_Plan_Document.docx) remains the baseline. Its 157 use-case IDs and four performance IDs are preserved in the [updated 207-case catalogue](../docs/Test_Case_Document.md), which is the current execution and traceability record. The catalogue includes 17 completion cases from the prior documentation draft, 17 current-branch feedback cases and 12 cases for 30 coverage follow-up tests of error and repeat-request paths.

Changes clarify OTP and temporary-password sequencing, safe identical attendance retries, required report scope/dates, private credential delivery and atomic recovery. Current-branch cases cover Admin-assisted password-reset requests, profile visibility, section batch year/edit/deletion and faculty subject scope. Missing malformed-email, blank-section and mark-preservation assertions were explicitly executed.

The testing method uses disposable PostgreSQL databases, synthetic accounts, captured email, a branch-instrumented full Django run, real local browser/TOTP journeys and the frozen BL29-v1 50-user capacity workload. The [four reports and submission index](../docs/README.md) contain fresh results, scope exclusions, skipped checks and outstanding acceptance items. Original manual inputs remain illustrative; only documented automated equivalents and recorded browser/performance executions are marked passed.

Full deployment acceptance is not declared: monthly uptime is not observed, and remaining platform/browser/device checks are open. SEC-07 was revised on 6 November 2026 to describe the implemented Admin-assisted reset ([BL-01 D-23](BL-01_Decision_Log.md)), which resolves the earlier token-link discrepancy (VAL-01). No additional development sprint or application feature change is part of this update.
