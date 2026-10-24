# Sprint 1 working-product demo

[Watch the 2-minute 6-second video](sprint-1-demo-video.mp4) · [SRT captions](sprint-1-demo-video.srt)

The 1080p video features actual browser interactions with the working application, a team introduction, chapter cards, captions and soft instrumental music with no voice. It credits **Harsha K, Pradhyut and Suhas** and uses a midnight-blue presentation theme. Its title cards, captions, cursor marker and soundtrack are video production elements, not changes to the application UI.

The demonstration includes attendance policy configuration: the Admin saves an **80%** attendance threshold, verifies that the dashboard flags **3 students** below the overall threshold, then restores the threshold to **75%**.

Sprint period: **19–23 October 2026**. Recorded on **24 October 2026**, using commit `a36b4bb` and fictional data in a separate local PostgreSQL database. The video preserves the browser walkthrough's pace and adds chapter cards.

| Time | Demonstration |
| --- | --- |
| 00:00–00:10 | Project, sprint and team introduction |
| 00:10–00:36 | Admin sign-in, dashboard, students, faculty and section roster |
| 00:36–00:54 | Attendance threshold configuration and dashboard updates |
| 00:54–01:25 | Faculty sign-in, attendance marking, save confirmation and persistence |
| 01:25–01:50 | Student sign-in, updated percentages and date-filtered result |
| 01:50–01:58 | Verified CI evidence |
| 01:58–02:06 | Closing credits |

## Evidence

- The demo starts with the existing [fictional test-data fixture](../../Documents/Test_Data_Fixture.md).
- Faculty F001 saves CS101 attendance: S001 Present, S002 Absent, S004 Present.
- S001's CS101 result changes from 74/100 to **75/101 (74.26%)**; overall changes from 76/103 to **77/104 (74.04%)**.
- Filtering S001's report to the recorded date, 24 October 2026, shows **1/1 (100.00%)**.
- [GitHub Actions run 39897650670](https://github.com/Harsha-Kamaraj/Student-Attendance-Management-System/actions/runs/39897650670), for commit `a36b4bb`, completed successfully on 23 October 2026. The log reports **249 tests passed**, plus successful lint, formatting and Django checks. The final card summarizes that existing run.

The video demonstrates the implemented workflow; it does not claim that all backlog items or performance tests are complete, or that owner PR reviews occurred.
