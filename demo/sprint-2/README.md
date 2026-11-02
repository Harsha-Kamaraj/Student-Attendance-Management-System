# Sprint 2 working-product demo

[Watch the video](sprint-2-demo-video.mp4) · [SRT subtitles](sprint-2-demo-video.srt) · [Poster](sprint-2-demo-poster.jpg)

**Duration:** 2 minutes 38.5 seconds. **Format:** 1920 × 1080, 30 fps, H.264 MP4 with AAC stereo audio.

The video follows Sprint 1's midnight-blue slide template: team introduction, numbered chapter cards, framed browser footage, explanatory subtitle strip and closing credits. It credits **Harsha K, Pradhyut and Suhas**. The soft instrumental soundtrack comes from the repository's Sprint 1 reference, with a crossfaded extension, normalized volume and opening/closing fades. There is no voice-over. Explanatory subtitles are burned into the walkthrough; the separate SRT also captions the title cards.

Sprint period: **26–30 October 2026**. Recorded on **2 November 2026**, using application commit `82790bd`, actual browser interactions and fictional data in a separate PostgreSQL database. The application code and development database were not changed for filming. Presentation frames, captions and the cursor marker are video production elements.

| Time | Demonstration |
| --- | --- |
| 00:00–00:09 | Project, sprint and team introduction |
| 00:09–00:26.5 | Faculty password and authenticator-code login; role dashboard |
| 00:26.5–01:04.5 | Save attendance, verify persistence, correct S001, inspect modification history |
| 01:04.5–01:28.8 | Date-filtered report and CSV/PDF downloads |
| 01:28.8–02:01 | Student totals, date filter and shortage notification |
| 02:01–02:29.5 | Admin overview, shortage list, encrypted backup creation and download |
| 02:29.5–02:38.5 | Closing credits |

## Verified recording outcomes

- Faculty F001 saves CS101 attendance for 2 November: S001 Absent, S002 Absent and S004 Present. Reloading retains the marks.
- F001 corrects S001 to Present with a reason. The audit history records the old/new status, editor, time and reason.
- The resulting class report has 3 marks: 2 Present and 1 Absent, or **66.67%**. The downloaded CSV has the expected three rows, and the PDF download has a valid PDF signature.
- S001 has **75/101 (74.26%)** in CS101 and **77/104 (74.04%)** overall. Filtering to the demonstration date shows **1/1 (100.00%)**.
- The notification shown was generated when the original absent mark was saved. Its percentages describe that event; the corrected current totals are shown separately in the dashboard and attendance page.
- Admin creates and downloads an encrypted backup. Download size and SHA-256 match the completed backup's catalogue entry.
- The recorded browser journey completed without JavaScript or server-response errors. The final MP4 was fully decoded, its audio level checked, and representative frames inspected for layout and subtitles.

Sanitized verification results are in [verification.json](verification.json). This video demonstrates these workflows; it does not present a new full regression, performance, email-delivery or restore test result. Demo emails stayed in a local memory backend.
