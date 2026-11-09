# Part 3 testing deliverables

Testing dates: 6 November 2026 (Part 3 run) and 9 November 2026 (full regression after the timetable, semester classes, send-login and interface changes). No Sprint 3 was created.

This folder contains the required updated test-case document and four reports:

- [Updated Test Case Document](Test_Case_Document.md) — 224 cases with steps, expected and actual outcomes, and test-method references.
- [Unit Test Report](Unit_Test_Report.pdf)
- [System Validation Report](System_Validation_Report.pdf)
- [Code Coverage Report](Code_Coverage_Report.pdf)
- [Branch Coverage Report](Branch_Coverage_Report.pdf)

Results on 9 November 2026: **552 tests passed, four skipped, zero failures/errors** (556 tests). Twelve browser cases (Chromium, Firefox and WebKit at 1440, 768, 360 and 320 px) passed. Line coverage is **95.10%**; branch coverage is **90.78%**. All four performance criteria passed on 9 November (1,000 students, 750,000 marks, 50 users). Five cases failed on first execution and were fixed and re-tested; the fix log is Section 7 of the [Test Plan](../Documents/Test_Plan_Document.docx).

The System Validation Report records outstanding requirements and deployment checks, including monthly uptime and remaining platform/device coverage. VAL-01 (the SEC-07 reset-token wording) was resolved by a specification change on 6 November 2026.

Detailed evidence, screenshots, HTML coverage pages and duplicate report formats are archived locally in `artifacts/part3/supporting-files-before-cleanup.zip` (6 November) and `artifacts/part3/rerun-2026-11-09/` (9 November) outside this submission folder. Paths to supporting files mentioned in the reports refer to entries inside that archive. The archive is excluded from Git by the existing artifacts rule.
