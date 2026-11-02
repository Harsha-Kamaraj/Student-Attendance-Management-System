# Part 3 testing documents

Prepared 2 November 2026 from existing test results. No application tests were rerun for document preparation.

| Required deliverable | File |
| --- | --- |
| Updated Test Case Document | [Test_Case_Document.docx](Test_Case_Document.docx) |
| Unit Test Report | [Unit_Test_Report.docx](Unit_Test_Report.docx) |
| System Validation Report | [System_Validation_Report.docx](System_Validation_Report.docx) |
| Code Coverage Report | [Code_Coverage_Report.docx](Code_Coverage_Report.docx) |
| Branch Coverage Report | [Branch_Coverage_Report.docx](Branch_Coverage_Report.docx) |

The [test plan](../Documents/Test_Plan_Document.docx) links the earlier 161 cases to the separate updated 178-case catalogue. Existing requirements, security and use-case documents contain directed consistency corrections. The source material retained its original dates; the 2-6 November activity window is a document/submission window, not a fabricated execution date.

## Evidence and qualifications

- Current source `c9fca90`: CI run 41185965165 passed 475 tests with 3 Windows-only skips out of 478 discovered. The named retained Windows baseline has 477 passing methods at readiness revision `42f0746`.
- Performance/environment and browser evidence is linked in the reports. Current-source browser-only run 41186435045 passed; it did not rerun backend/performance jobs.
- Code and branch coverage reports explicitly record **not measured**. No line/arc coverage artifact exists in the inspected runs; test pass counts are not structural coverage percentages.
- Monthly deployment availability, external transport/delivery and the complete physical-device/native-browser/version matrix are not established by the local records.
- Catalogue result conventions distinguish mapped automated equivalents from literal manual fixture execution. Related but incomplete evidence is marked partial.

## Traceability files

- [Document corrections and remaining evidence limits](Document_Review.md)
- [Per-case evidence and qualifications](evidence/test_case_evidence.csv)
- [Exact named test outcomes](evidence/named_test_results.csv)
- [Current-source CI summary](evidence/latest_ci_summary.json)
- [Prior complete verification](../Documents/Verification/BL-29-30_Readiness.md)

Catalogue status counts: PARTIAL evidence: 3, PASS automated equivalent: 171, PASS in recorded profile: 4.
