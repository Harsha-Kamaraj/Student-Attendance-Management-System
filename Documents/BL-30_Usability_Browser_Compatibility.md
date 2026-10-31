# BL-30: Usability and browser compatibility

The responsive-layout fixes and automated browser journeys are implemented. The evidence below records
actual browser/engine versions and viewport sizes. The complete BL-01 D-16 target remains the latest two
versions of Chrome, Edge, Firefox and Safari on desktop, plus Chrome on Android and Safari on iOS at
360px. A passing engine or emulated viewport does not certify every branded release or a physical device.

## Fixes

- Removed literal Markdown fences from the shared HTML template. Pages now enter standards mode.
- Serve pinned Bootstrap 5.3.3 locally, with its MIT license. Styling does not depend on a public CDN.
- Wrap long navigation identities without pushing controls outside the viewport.
- Keep table headers and identifiers readable. Narrow screens scroll the table instead of the page.
- Give scrolling tables an accessible name, visible keyboard focus and arrow-key scrolling, including
  the WebKit mobile case that did not scroll with its native key behavior.
- Add a doctype regression test and real browser journeys that check readability as well as overflow.

The defects and retests are tracked in [#54](https://github.com/Harsha-Kamaraj/Student-Attendance-Management-System/issues/54).

## Executed browser coverage

| Host | Browser / engine actually tested | Widths | Role workflows |
| --- | --- | --- | --- |
| macOS | Installed Chrome 156.0.8078.74 | 1440px, 360px | Admin, Faculty, Student |
| macOS | Playwright Chromium 156.0.8078.4 | 1440px, 360px | Admin, Faculty, Student |
| macOS | Playwright Firefox 157.0 | 1440px, 360px | Admin, Faculty, Student |
| macOS | Playwright WebKit 27.2 | 1440px, 360px | Admin, Faculty, Student |
| Ubuntu | Playwright Chromium, Firefox and WebKit | 1440px, 360px | Admin, Faculty, Student |
| Windows Server 2025 | Installed Chrome 156.0.8078.48 | 1440px, 360px | Admin, Faculty, Student |
| Windows Server 2025 | Installed Edge 155.0.4283.62 | 1440px, 360px | Admin, Faculty, Student |

The JSON evidence records exact versions on every case. The 360px cases use viewport/touch emulation.
WebKit is identified as WebKit, not as a completed native Safari test. These distinctions follow the
[Playwright browser documentation](https://playwright.dev/python/docs/browsers).

The Mac matrix has eight cases, Ubuntu six and Windows four: **18 cases / 54 role journeys**. Each
journey uses real password and TOTP setup/login with the application's default password hashing;
there is no password-only authentication bypass. All requests outside the local test server are blocked.

## Workflows and usability assertions

Admin checks dashboards, long navigation identities, student tables, required-field messages and
empty report selections. Faculty checks assigned classes, incomplete rosters, the bulk-Present control,
saving, correction/history and empty rosters. Students check current totals, invalid date ranges,
empty filtered results and empty notifications. Every role signs out through the actual browser UI.

Each checkpoint verifies standards mode, loaded local styling, readable table-header heights,
no document-wide horizontal overflow, visible control bounds, accessible form labels and named,
keyboard-focusable table scrollers. The narrow cases also execute arrow-key scrolling. JavaScript
errors fail the case. Screenshots are saved after login; passwords, OTP setup keys and backup codes
are not captured.

A visual review caught the compressed Roll number column after an initial geometry-only run passed.
The header-readability assertion and scrollable-column fix were then added and retested. A WebKit
mobile keyboard-scroll failure was fixed explicitly. The test runner also waits for page/stylesheet
loading before measuring layout, avoiding assertions against a transient unstyled DOM.

See the [readiness report](Verification/BL-29-30_Readiness.md) for retained JSON, screenshots, checksums,
performance/regression outcomes and GitHub runs. Earlier failed diagnostics are described there;
only completed passing cases count toward the executed matrix.

## Reproduce

Use an empty disposable local PostgreSQL database named `verification_bl29_browser_<suffix>`.
Set explicit `DATABASE_URL` and `SECRET_KEY`, then run:

```bash
pip install -r requirements-browser.txt
python -m playwright install chromium firefox webkit
python manage.py migrate --noinput
python -m verification.browser_check --engines chromium firefox webkit --widths 1440 360 --out artifacts/browser/results.json
```

To test installed branded browsers, use `--engines chrome msedge`. A missing requested browser is a
failure, never a silently passing case. The runner refuses populated application data. Use a new
empty database and output directory for each execution. It changes only its synthetic fixture.

The manually dispatched verification workflow can run `scope=all`, `scope=browsers`, or
`scope=performance`. Browser jobs run on Ubuntu and Windows and retain versions, outcomes and screenshots.

## Remaining matrix acceptance

Native Safari, previous branded browser releases, real Android Chrome and real iOS Safari still need
separate executions. No observation of those environments is inferred from Playwright's engines.
Record the browser version, operating system, viewport, role, workflow, result and any defect/retest
for each additional run before claiming the full latest-two-version/device matrix is complete.
