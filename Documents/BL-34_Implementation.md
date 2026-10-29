# BL-34 — Email login details (#42)

Implemented for UC-02 student creation, UC-03 faculty creation, Admin password resets and explicit resends. Existing Admin-account creation keeps its private one-time screen handover.

| Requirement | Implementation / verification |
| --- | --- |
| Own recipient only | A plain-text email contains username, generated temporary password and the configured login URL; exactly one To recipient, no CC/BCC, names, department or attendance data. |
| Creation and reset | Creation sends only after account, profile and audit writes succeed. Resets save a new salted hash and clear password lockout before delivery. First-login change and OTP remain enforced. |
| No readable stored password | The generated password stays in request memory. It is absent from sessions, audit records, persisted email queues and successful response pages. Sensitive-variable decorators protect production error reports. |
| Honest delivery feedback | Admin sees a masked address and success/failure. SMTP exceptions, including ones containing secrets, are discarded. A return value of zero is a failure. The development console is explicitly described as a preview. |
| Failure fallback | The account/profile remains saved. The current password is displayed only on the non-cacheable response page; no retrieval endpoint or session copy exists. |
| Resend | Admin-only CSRF-protected POST, for active temporary-password accounts. Generates a new password, invalidating the old one. If the user already changed it, resend is rejected; an explicit reset is required. |
| Audit | `credentials.email_attempt`, `credentials.email_sent`, `credentials.email_failed`, `credentials.email_preview`; metadata includes purpose (`created`, `reset`, `resend`), masked address and safe outcome only. |
| Concurrent changes | Reset and delivery lock the account row. Delivery rechecks the current password and email; a superseded password is neither emailed nor displayed. |
| Configuration | Existing `.env` email settings plus `SITE_URL`; HTTPS required outside development. No request-host-derived login link, provider credentials or real addresses committed. |

## Configuration and operating limits

Set `SITE_URL=https://your-attendance-host` and the SMTP backend/host/port/user/password, sender address and TLS/SSL options in `.env`. No new background worker or schema migration is required. Delivery is synchronous and subject to `EMAIL_TIMEOUT`; transport acceptance does not guarantee inbox delivery.

The console backend is a development-only exception for previewing fictional credentials, as required by the backlog; do not capture previews in persistent logs. Production console, file-based and dummy credential delivery are refused. Tests use Django's in-memory email backend and fictional accounts. Missing/invalid email or configuration preserves the one-time fallback.

If the process dies after the account commit, resend rotates the password and recovers access without storing plaintext for retries. Keep the same application database owner for the existing audit and row-lock behavior.

## Acceptance tests

`python manage.py test apps.accounts.test_credential_email` covers both creation paths, resets, resends, forced password change, recipient/content privacy, HTML-safe fallback, zero-return and exception failures, console preview, prohibited storage backends, invalid production URL, spoofed Host, duplicate/invalid submissions, profile rollback, stale credentials, authorization and CSRF. Existing student/faculty tests now read successful credentials from the test email rather than the Admin page.

The SRS (AR-01), security specification (SEC-05/06/25/27/28), use cases UC-02/UC-03 and test plan contain the BL-34 updates and acceptance mapping.
