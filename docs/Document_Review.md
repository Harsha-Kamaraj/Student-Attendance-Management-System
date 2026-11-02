# Part 3 document review

Prepared 2 November 2026 against source `c9fca90` and existing execution records. This update changes documents only.

## Corrections made

- Preserved all 161 earlier test-case IDs and added 17 cases for credential delivery, explicit report scope/section authorization, denominator consistency and browser standards.
- Included each supplied case parameter: ID, scenario, description, setup, prerequisites, steps, parameters, expected result, actual result and comments.
- Added exact evidence IDs and separate CSV records for the 477 named Windows outcomes. Current-revision CI results are recorded separately: 478 discovered, 475 passed and three native Windows skips.
- Corrected the order of OTP and forced password change, an inconsistent logged-out prerequisite, and the distinction between an identical attendance retry and a changed retry.
- Aligned SRS/use-case/report wording with required scope and dates, private credential delivery and atomic recovery safeguards.
- Extended the outdated security-reference range to SEC-01 through SEC-32 and aligned the earlier README handover description with BL-34.
- Moved the detailed case catalogue to `docs/Test_Case_Document.docx`, retaining a readable plan and its links at `Documents/Test_Plan_Document.docx`.
- Corrected table widths, repeated headers, title rules, row/page splitting and an unnecessary blank page. The final Word documents were rendered and their pages visually checked.

## Evidence limits retained

1. **Code and branch coverage:** inspected workflows/artifacts contain no instrumentation or executed-line/arc data. Both required reports exist, but correctly mark quantitative coverage as not measured. Passing tests are not a coverage percentage.
2. **Manual versus automated execution:** a passed automated equivalent does not establish that every literal manual example was entered. `UT_02_3`, `UT_05_2` and `UT_06_6` retain partial-evidence labels for assertions not independently established by the mapped record.
3. **Revision binding:** readiness capacity/performance and named Windows outcomes were recorded on `42f0746`. Current revision `c9fca90` has separate successful CI and browser-only workflow records; no new load run is asserted for that later UI revision.
4. **Deployment acceptance:** monthly 99% institutional-hours availability, real deployment transport/delivery and the full native browser/version/physical-device matrix remain outside the available local evidence.
5. **Requirement scope:** the reports do not declare every security requirement independently verified. For example, SEC-07's forgotten-password token-link behavior needs its own execution record; Admin password-reset evidence alone does not establish that flow.

The original source documents and earlier failed test observations remain in Git history. The reports preserve actual execution dates rather than changing them to the 2-6 November submission window.
