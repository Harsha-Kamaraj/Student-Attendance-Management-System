# Updated Test Case Document

Project: Student Attendance Management System. Activity: Part 3 testing of completed Sprint 1 and Sprint 2 work. Execution dates: 6 November 2026 (Part 3 run) and 9 November 2026 (full regression after the timetable, semester classes, send-login and interface changes). Branch: `main`. No Sprint 3 was started.

## Scope and result conventions

The detailed execution evidence referenced below is retained in a separate local supporting-files archive. This folder contains the required submission documents only.

This catalogue contains 224 cases. It preserves the 157 use-case IDs from the current Test Plan, the four performance cases, and the 17 previously drafted completion cases, then adds 17 cases for current-branch feedback changes, 12 cases for the coverage follow-up tests and 17 cases for the 9 November changes (FR-22 to FR-24). The earlier `origin/sprint2/final-documentation` catalogue supplied the definitions and candidate mappings; result labels were resolved against fresh execution on 6 November, and the full rerun on 9 November (556 tests: 552 passed, 4 skipped) passed every mapped method again. Original case IDs are retained.

The legacy UT, IT and ST prefixes are plan identifiers, not proof of test isolation level. Some UT cases use the database or HTTP client. Automated equivalents use the exact linked methods and their own fixtures. No manual acceptance signature is implied.

| Result | Cases |
| --- | --- |
| PASS automated equivalent | 219 |
| PASS browser execution | 1 |
| PASS local performance profile | 4 |

## Changes since the earlier plan

- Clarified password, OTP enrollment/verification and forced-password-change ordering.
- Updated class/section wording to Dept and sem with optional batch year.
- Distinguished an identical attendance retry from a changed duplicate submission.
- Preserved explicit report scope/date rules, credential email privacy and atomic recovery safeguards.
- Closed the three earlier evidence gaps for malformed student email, required section fields and preservation of explicit marks.
- Added catalogue cases for Admin-assisted forgotten passwords, privacy/rate limits, profile visibility, section year/edit/deletion and faculty subject scope.
- Measured code and branch coverage instead of inferring percentages from test pass counts.
- Added 12 cases (UT_01_14, IT_01_8, UT_02_4, UT_02_5, ST_02_8, IT_05_7, UT_06_7, UT_07_6, ST_07_6, UT_13_4, UT_13_5, UT_12_5) for 30 coverage follow-up tests of error and repeat-request paths. A later full rerun on 6 November passed every method mapped by all 207 cases.
- Added 17 cases on 9 November 2026 for the new requirements FR-22 to FR-24 and decisions D-27 and D-28: UT_01_15–17 and IT_01_9 (send login details), IT_11_4 (history after filtering), IT_12_5–6 (dashboard counts and sidebar), UT_14_1–7 and IT_14_1–3 (timetable, semester classes and attendance advice). The 9 November full rerun passed every method mapped by all 224 cases.

Coverage totals and environment acceptance limits are in the four companion reports. SEC-07 was revised on 6 November 2026 to describe the implemented Admin-assisted reset (BL-01 D-23); the forgotten-password cases IT_01_6–7, UT_01_9–10 and UT_01_13 trace to the revised requirement.

## Shared prerequisites

Use disposable local PostgreSQL databases, fictional accounts, captured email and temporary encrypted backup storage. Browser journeys require password and OTP; legacy component tests use the project runner with OTP disabled unless the test explicitly enables it. Fixtures create the necessary roles, sections, subjects, enrollments and marks. Manual example names and passwords are illustrative fixture values, never production credentials.

## UT_01_1  Verify Login & Role-Based Access succeeds with valid input.

**Module:** Authentication / BL-04, BL-05

**Preconditions:** User has an active account created by the Admin.

**Parameters:**  S001 / Attend#2026 (fixture).

**Steps:** 1: Open the login page and enter valid credentials. 2: Complete first-login OTP setup if needed, then verify a one-time code. 3: Complete any forced temporary-password change. 4: Open the role-specific dashboard and verify the displayed role. 5: Log out. Complete OTP verification or first-login enrollment before opening protected pages; complete a forced password change when required.

**Expected result:** Login succeeds and the Student dashboard opens with 'S001 · Student' in the top bar.

**Actual result:** Fresh execution: 2 mapped test method(s) passed. Assertions cover the automated equivalent described by the named methods; this is not a claim of a separate literal manual execution.

**Result:** PASS automated equivalent

**Evidence:** `evidence/part3-2026-11-06/regression.json` (archived)

**Exact test methods:**

- `apps.accounts.tests.LoginTests.test_each_role_reaches_its_dashboard`
- `apps.accounts.test_otp.AuthenticatorCodeTests.test_correct_code_completes_login`

**Qualification:** Automated equivalent using isolated synthetic fixtures; literal manual example accounts and counts were not separately executed.

## UT_01_2  Verify login is rejected when the username or password is blank.

**Module:** Authentication / BL-04, BL-05

**Preconditions:** User has an active account created by the Admin.

**Parameters:**  Blank username and password; then blank password.

**Steps:** 1: Open /login/. 2: Leave both fields empty and click Log in. 3: Repeat with only the password empty.

**Expected result:** 'This field is required.' appears under each empty field; no session is created.

**Actual result:** Fresh execution: 1 mapped test method(s) passed. Assertions cover the automated equivalent described by the named methods; this is not a claim of a separate literal manual execution.

**Result:** PASS automated equivalent

**Evidence:** `evidence/part3-2026-11-06/regression.json` (archived)

**Exact test methods:**

- `apps.accounts.tests.LoginTests.test_blank_fields_are_rejected`

**Qualification:** Automated equivalent using isolated synthetic fixtures; literal manual example accounts and counts were not separately executed.

## UT_01_3  Verify unknown usernames and wrong passwords get the same generic message (SEC-02).

**Module:** Authentication / BL-04, BL-05

**Preconditions:** User has an active account created by the Admin.

**Parameters:**  Unknown username; wrong password for S001.

**Steps:** 1: Log in as NOBODY / Attend#2026. 2: Log in as S001 / Wrong#2026.

**Expected result:** Both attempts show exactly 'Invalid username or password.'; no session is created; both failures are logged.

**Actual result:** Fresh execution: 1 mapped test method(s) passed. Assertions cover the automated equivalent described by the named methods; this is not a claim of a separate literal manual execution.

**Result:** PASS automated equivalent

**Evidence:** `evidence/part3-2026-11-06/regression.json` (archived)

**Exact test methods:**

- `apps.accounts.tests.LoginTests.test_wrong_username_and_wrong_password_show_the_same_message`

**Qualification:** Automated equivalent using isolated synthetic fixtures; literal manual example accounts and counts were not separately executed.

## UT_01_4  Verify that self-registration is not available (AR-01).

**Module:** Authentication / BL-04, BL-05

**Preconditions:** User is not logged in.

**Parameters:**  No account; registration address.

**Steps:** 1: Open the login page. 2: Look for a sign-up option. 3: Request a registration address directly (e.g. /register).

**Expected result:** No sign-up option is shown; the direct request returns "not found" or redirects to login; no account is created.

**Actual result:** Fresh execution: 1 mapped test method(s) passed. Assertions cover the automated equivalent described by the named methods; this is not a claim of a separate literal manual execution.

**Result:** PASS automated equivalent

**Evidence:** `evidence/part3-2026-11-06/regression.json` (archived)

**Exact test methods:**

- `apps.accounts.tests.LoginTests.test_no_self_registration`

**Qualification:** Automated equivalent using isolated synthetic fixtures; literal manual example accounts and counts were not separately executed.

## UT_01_5  Verify a correct password alone does not log the user in (SEC-29).

**Module:** Authentication / BL-33

**Preconditions:** OTP is enabled; S001 has set up an authenticator app.

**Parameters:**  S001 / Attend#2026; no code.

**Steps:** 1: Log in as S001 with the correct password. 2: Without entering a code, open /dashboard/.

**Expected result:** The code page is shown; /dashboard/ redirects back to it; no dashboard is reachable.

**Actual result:** Fresh execution: 1 mapped test method(s) passed. Assertions cover the automated equivalent described by the named methods; this is not a claim of a separate literal manual execution.

**Result:** PASS automated equivalent

**Evidence:** `evidence/part3-2026-11-06/regression.json` (archived)

**Exact test methods:**

- `apps.accounts.test_otp.PasswordAloneTests.test_password_alone_does_not_reach_a_dashboard`

**Qualification:** Automated equivalent using isolated synthetic fixtures; literal manual example accounts and counts were not separately executed.

## UT_01_6  Verify wrong codes are rejected and 5 wrong codes lock the account (SEC-32).

**Module:** Authentication / BL-33

**Preconditions:** OTP is enabled; S001 has set up an authenticator app.

**Parameters:**  Wrong code 000000 five times.

**Steps:** 1: Enter the password, then a wrong 6-digit code 5 times. 2: Enter the correct password and a valid code.

**Expected result:** Each wrong code shows an error; after the 5th the account is locked for 15 minutes and even a valid code is refused; every attempt is logged.

**Actual result:** Fresh execution: 1 mapped test method(s) passed. Assertions cover the automated equivalent described by the named methods; this is not a claim of a separate literal manual execution.

**Result:** PASS automated equivalent

**Evidence:** `evidence/part3-2026-11-06/regression.json` (archived)

**Exact test methods:**

- `apps.accounts.test_otp.LockoutTests.test_five_wrong_codes_lock_the_account`

**Qualification:** Automated equivalent using isolated synthetic fixtures; literal manual example accounts and counts were not separately executed.

## UT_01_7  Verify emailed codes expire after 10 minutes, work once, and are rate-limited (SEC-32).

**Module:** Authentication / BL-33

**Preconditions:** OTP is enabled; S001 has set up an authenticator app.

**Parameters:**  Emailed codes for S001.

**Steps:** 1: Request an emailed code and use it. 2: Use the same code again. 3: Request a code and wait 11 minutes before using it. 4: Request 4 codes within 15 minutes.

**Expected result:** Step 1 logs in; step 2 is rejected; step 3 is rejected as expired; the 4th request in step 4 is refused.

**Actual result:** Fresh execution: 3 mapped test method(s) passed. Assertions cover the automated equivalent described by the named methods; this is not a claim of a separate literal manual execution.

**Result:** PASS automated equivalent

**Evidence:** `evidence/part3-2026-11-06/regression.json` (archived)

**Exact test methods:**

- `apps.accounts.test_otp.EmailCodeTests.test_emailed_code_expires_after_10_minutes`
- `apps.accounts.test_otp.EmailCodeTests.test_at_most_3_emailed_codes_in_15_minutes`
- `apps.accounts.test_otp.EmailCodeTests.test_emailed_code_is_sent_only_to_the_user_and_works_once`

**Qualification:** Automated equivalent using isolated synthetic fixtures; literal manual example accounts and counts were not separately executed.

## UT_01_8  Verify a backup code works once (SEC-31).

**Module:** Authentication / BL-33

**Preconditions:** OTP is enabled; S001 has set up an authenticator app.

**Parameters:**  One of S001's 10 backup codes.

**Steps:** 1: Log in with the password and backup code #1. 2: Log out and try backup code #1 again.

**Expected result:** Step 1 logs in; step 2 is rejected; the remaining backup count drops from 10 to 9.

**Actual result:** Fresh execution: 1 mapped test method(s) passed. Assertions cover the automated equivalent described by the named methods; this is not a claim of a separate literal manual execution.

**Result:** PASS automated equivalent

**Evidence:** `evidence/part3-2026-11-06/regression.json` (archived)

**Exact test methods:**

- `apps.accounts.test_otp.BackupCodeTests.test_backup_code_works_once`

**Qualification:** Automated equivalent using isolated synthetic fixtures; literal manual example accounts and counts were not separately executed.

## IT_01_1  Verify the account's role decides the dashboard the user reaches.

**Module:** Authentication / BL-04, BL-05

**Preconditions:** User has an active account created by the Admin.

**Parameters:**  ADMIN1, F001, S001 / Attend#2026.

**Steps:** 1: Log in as ADMIN1, F001 and S001 in turn. 2: Note the dashboard and the role shown in the top bar. Complete OTP verification or first-login enrollment before opening protected pages; complete a forced password change when required.

**Expected result:** ADMIN1 reaches the Admin dashboard ( /  Admin); F001 the Faculty dashboard ( /  Faculty); S001 the Student dashboard ( /  Student).

**Actual result:** Fresh execution: 2 mapped test method(s) passed. Assertions cover the automated equivalent described by the named methods; this is not a claim of a separate literal manual execution.

**Result:** PASS automated equivalent

**Evidence:** `evidence/part3-2026-11-06/regression.json` (archived)

**Exact test methods:**

- `apps.accounts.tests.LoginTests.test_each_role_reaches_its_dashboard`
- `apps.accounts.test_otp.AuthenticatorCodeTests.test_correct_code_completes_login`

**Qualification:** Automated equivalent using isolated synthetic fixtures; literal manual example accounts and counts were not separately executed.

## IT_01_2  Verify a logged-in user cannot open another role's pages (SEC-10).

**Module:** Authentication / BL-04, BL-05

**Preconditions:** S001 and F001 are logged in (separate browsers). Password and OTP verification are complete; any required first-login password change is complete.

**Parameters:**  S001 and F001 credentials.

**Steps:** 1: As S001, open /dashboard/admin/ and /users/. 2: As F001, open /dashboard/admin/.

**Expected result:** Each request shows 'Access denied' (HTTP 403) with no Admin data; each denial is logged as access.denied.

**Actual result:** Fresh execution: 2 mapped test method(s) passed. Assertions cover the automated equivalent described by the named methods; this is not a claim of a separate literal manual execution.

**Result:** PASS automated equivalent

**Evidence:** `evidence/part3-2026-11-06/regression.json` (archived)

**Exact test methods:**

- `apps.accounts.tests.LoginTests.test_user_cannot_open_another_roles_dashboard`
- `apps.accounts.test_permissions.DenialTests.test_denial_is_logged_with_user_and_path`

**Qualification:** Automated equivalent using isolated synthetic fixtures; literal manual example accounts and counts were not separately executed.

## IT_01_3  Verify a changed password persists after logout and login.

**Module:** Authentication / BL-04, BL-05

**Preconditions:** S001 is logged in. Password and OTP verification are complete; any required first-login password change is complete.

**Parameters:**  Old Attend#2026; new New#Pass2026.

**Steps:** 1: Change S001's password to New#Pass2026. 2: Log out. 3: Log in with the old password, then the new one.

**Expected result:** The old password is rejected; the new password logs in to the Student dashboard.

**Actual result:** Fresh execution: 1 mapped test method(s) passed. Assertions cover the automated equivalent described by the named methods; this is not a claim of a separate literal manual execution.

**Result:** PASS automated equivalent

**Evidence:** `evidence/part3-2026-11-06/regression.json` (archived)

**Exact test methods:**

- `apps.accounts.tests.FirstLoginTests.test_full_first_login_flow`

**Qualification:** Automated equivalent using isolated synthetic fixtures; literal manual example accounts and counts were not separately executed.

## IT_01_4  Verify an Admin can reset a user's OTP only after re-entering their own password (SEC-31).

**Module:** Authentication / BL-33

**Preconditions:** ADMIN1 is logged in; F001 has OTP set up. Password and OTP verification are complete; any required first-login password change is complete.

**Parameters:**  ADMIN1 password Attend#2026.

**Steps:** 1: Choose Reset OTP for F001 and leave the Admin password blank. 2: Repeat with ADMIN1's password. 3: Log in as F001.

**Expected result:** Step 1 is refused; step 2 resets F001's OTP and is logged; at step 3 F001 must set up the authenticator app again.

**Actual result:** Fresh execution: 2 mapped test method(s) passed. Assertions cover the automated equivalent described by the named methods; this is not a claim of a separate literal manual execution.

**Result:** PASS automated equivalent

**Evidence:** `evidence/part3-2026-11-06/regression.json` (archived)

**Exact test methods:**

- `apps.accounts.test_otp.AdminResetTests.test_reset_needs_the_admins_password`
- `apps.accounts.test_otp.AdminResetTests.test_reset_clears_otp_and_forces_setup_again`

**Qualification:** Automated equivalent using isolated synthetic fixtures; literal manual example accounts and counts were not separately executed.

## IT_01_5  Verify the setup secret is never exposed after setup (SEC-30).

**Module:** Authentication / BL-33

**Preconditions:** S002 is setting up OTP.

**Parameters:**  S002's setup secret.

**Steps:** 1: Complete setup. 2: Search the audit log, server log and any emails for the secret shown during setup.

**Expected result:** The secret appears nowhere except the setup page; backup codes are stored only as hashes.

**Actual result:** Fresh execution: 2 mapped test method(s) passed. Assertions cover the automated equivalent described by the named methods; this is not a claim of a separate literal manual execution.

**Result:** PASS automated equivalent

**Evidence:** `evidence/part3-2026-11-06/regression.json` (archived)

**Exact test methods:**

- `apps.accounts.test_otp.SetupTests.test_secret_never_appears_in_the_audit_log_or_emails`
- `apps.accounts.test_otp.BackupCodeTests.test_backup_codes_are_stored_only_as_hashes`

**Qualification:** Automated equivalent using isolated synthetic fixtures; literal manual example accounts and counts were not separately executed.

## ST_01_1  End-to-end system test: complete the full "Login & Role-Based Access" workflow as an actual user would.

**Module:** Authentication / BL-04, BL-05

**Preconditions:** User has an active account created by the Admin.

**Parameters:**  ADMIN1, F001, S001 / Attend#2026.

**Steps:** 1: Open the login page and enter valid credentials. 2: Complete first-login OTP setup if needed, then verify a one-time code. 3: Complete any forced temporary-password change. 4: Open the role-specific dashboard and verify the displayed role. 5: Log out. Complete OTP verification or first-login enrollment before opening protected pages; complete a forced password change when required.

**Expected result:** Each user lands on the dashboard for their role with their username and role in the top bar; Log out returns to the login page.

**Actual result:** Fresh execution: 2 mapped test method(s) passed. Assertions cover the automated equivalent described by the named methods; this is not a claim of a separate literal manual execution.

**Result:** PASS automated equivalent

**Evidence:** `evidence/part3-2026-11-06/regression.json` (archived)

**Exact test methods:**

- `apps.accounts.tests.LoginTests.test_each_role_reaches_its_dashboard`
- `apps.accounts.test_otp.AuthenticatorCodeTests.test_correct_code_completes_login`

**Qualification:** Automated equivalent using isolated synthetic fixtures; literal manual example accounts and counts were not separately executed.

## ST_01_2  System test: verify the exception flow  -  Invalid credentials: system shows an error and does not log the user in.

**Module:** Authentication / BL-04, BL-05

**Preconditions:** User has an active account created by the Admin.

**Parameters:**  S001 / Wrong#2026.

**Steps:** 1: Enter S001 with password Wrong#2026. 2: Click Log in.

**Expected result:** 'Invalid username or password.' is shown and the user is not logged in.

**Actual result:** Fresh execution: 1 mapped test method(s) passed. Assertions cover the automated equivalent described by the named methods; this is not a claim of a separate literal manual execution.

**Result:** PASS automated equivalent

**Evidence:** `evidence/part3-2026-11-06/regression.json` (archived)

**Exact test methods:**

- `apps.accounts.tests.LoginTests.test_wrong_username_and_wrong_password_show_the_same_message`

**Qualification:** Automated equivalent using isolated synthetic fixtures; literal manual example accounts and counts were not separately executed.

## ST_01_3  Verify a deactivated account cannot log in (UC-01 3b, SEC-15, AR-03).

**Module:** Authentication / BL-04, BL-05

**Preconditions:** Admin has deactivated student S1.

**Parameters:**  S1 (deactivated), correct password.

**Steps:** 1: Log in as S1 with the correct password.

**Expected result:** Inactive accounts receive the generic login rejection and cannot open protected resources; the failed attempt is audited.

**Actual result:** Fresh execution: 1 mapped test method(s) passed. Assertions cover the automated equivalent described by the named methods; this is not a claim of a separate literal manual execution.

**Result:** PASS automated equivalent

**Evidence:** `evidence/part3-2026-11-06/regression.json` (archived)

**Exact test methods:**

- `apps.accounts.tests.LoginTests.test_deactivated_account_cannot_log_in`

**Qualification:** Automated equivalent using isolated synthetic fixtures; literal manual example accounts and counts were not separately executed.

## ST_01_4  Verify a reactivated account can log in again (AR-03).

**Module:** Authentication / BL-04, BL-05

**Preconditions:** Admin has reactivated student S1.

**Parameters:**  S1 (reactivated), correct password.

**Steps:** 1: Log in as S1 with the correct password. Complete OTP verification or first-login enrollment before opening protected pages; complete a forced password change when required.

**Expected result:** Login succeeds and the Student dashboard is shown.

**Actual result:** Fresh execution: 1 mapped test method(s) passed. Assertions cover the automated equivalent described by the named methods; this is not a claim of a separate literal manual execution.

**Result:** PASS automated equivalent

**Evidence:** `evidence/part3-2026-11-06/regression.json` (archived)

**Exact test methods:**

- `apps.accounts.tests.LoginTests.test_reactivated_account_can_log_in`

**Qualification:** Automated equivalent using isolated synthetic fixtures; literal manual example accounts and counts were not separately executed.

## ST_01_5  Verify a new account must change its temporary password at first login (SEC-06, AR-01).

**Module:** Authentication / BL-04, BL-05

**Preconditions:** Admin has just created student S3.

**Parameters:**  S3 temporary password; new password Attend#2026.

**Steps:** 1: Sign in with the new temporary password. 2: Complete OTP setup/code verification. 3: Attempt a protected page before changing the password. 4: Set a compliant new password and open the dashboard.

**Expected result:** OTP completes first. The temporary-password change is then required before any protected action; after both gates complete, the Student dashboard is available.

**Actual result:** Fresh execution: 1 mapped test method(s) passed. Assertions cover the automated equivalent described by the named methods; this is not a claim of a separate literal manual execution.

**Result:** PASS automated equivalent

**Evidence:** `evidence/part3-2026-11-06/regression.json` (archived)

**Exact test methods:**

- `apps.accounts.tests.FirstLoginTests.test_full_first_login_flow`

**Qualification:** Automated equivalent using isolated synthetic fixtures; literal manual example accounts and counts were not separately executed.

## ST_01_6  End-to-end first login with OTP setup (UC-01 3c, SEC-06, SEC-30).

**Module:** Authentication / BL-33

**Preconditions:** The Admin has just created student S005 with a temporary password.

**Parameters:**  S005; Google or Microsoft Authenticator.

**Steps:** 1: Log in as S005 with the temporary password. 2: Scan the QR code with an authenticator app and enter its code. 3: Save the 10 backup codes. 4: Change the temporary password.

**Expected result:** No other page opens until OTP is set up and the password is changed; the backup codes are shown once; S005 then reaches the Student dashboard.

**Actual result:** Fresh execution: 1 mapped test method(s) passed. Assertions cover the automated equivalent described by the named methods; this is not a claim of a separate literal manual execution.

**Result:** PASS automated equivalent

**Evidence:** `evidence/part3-2026-11-06/regression.json` (archived)

**Exact test methods:**

- `apps.accounts.test_otp.SetupTests.test_first_login_with_temporary_password_sets_up_otp_then_changes_password`

**Qualification:** Automated equivalent using isolated synthetic fixtures; literal manual example accounts and counts were not separately executed.

## ST_01_7  Verify every role must use OTP and is asked again at every login (SEC-29).

**Module:** Authentication / BL-33

**Preconditions:** ADMIN1, F001 and S001 have OTP set up.

**Parameters:**  ADMIN1, F001, S001.

**Steps:** 1: Log in as each user. 2: Log out and log in again as the same user. Complete OTP verification or first-login enrollment before opening protected pages; complete a forced password change when required.

**Expected result:** Each login, including the second one, asks for a one-time code before the dashboard; there is no 'remember this device' option.

**Actual result:** Fresh execution: 2 mapped test method(s) passed. Assertions cover the automated equivalent described by the named methods; this is not a claim of a separate literal manual execution.

**Result:** PASS automated equivalent

**Evidence:** `evidence/part3-2026-11-06/regression.json` (archived)

**Exact test methods:**

- `apps.accounts.test_otp.PasswordAloneTests.test_every_role_must_set_up_otp`
- `apps.accounts.test_otp.AuthenticatorCodeTests.test_no_remember_this_device`

**Qualification:** Automated equivalent using isolated synthetic fixtures; literal manual example accounts and counts were not separately executed.

## UT_02_1  Verify Manage Students succeeds with valid input.

**Module:** Student Management / BL-07

**Preconditions:** Admin is logged in. Password and OTP verification are complete; any required first-login password change is complete.

**Parameters:**  Roll number 21CS001, name "Test Student 1", class 2, section A.

**Steps:** 1: Admin opens the Student Management screen. 2: Admin adds a new student with roll number, name, class, and section. 3: System validates the data and checks for duplicate roll numbers.

**Expected result:** Student and login are saved. The username, temporary password and login link are emailed only to the student; the Admin sees masked delivery status (BL-34).

**Actual result:** Fresh execution: 1 mapped test method(s) passed. Assertions cover the automated equivalent described by the named methods; this is not a claim of a separate literal manual execution.

**Result:** PASS automated equivalent

**Evidence:** `evidence/part3-2026-11-06/regression.json` (archived)

**Exact test methods:**

- `apps.accounts.test_credential_email.CredentialEmailTests.test_student_creation_emails_only_owner_and_hides_successful_password`

**Qualification:** Automated equivalent using isolated synthetic fixtures; literal manual example accounts and counts were not separately executed.

## UT_02_2  Verify Add student rejects blank required fields.

**Module:** Student Management / BL-07

**Preconditions:** Admin is logged in. Password and OTP verification are complete; any required first-login password change is complete.

**Parameters:**  All fields blank.

**Steps:** 1: Open Manage students  >  Add student. 2: Leave roll number, name, class, section and email empty. 3: Click Save.

**Expected result:** 'This field is required.' under each field; no student or account is created.

**Actual result:** Fresh execution: 1 mapped test method(s) passed. Assertions cover the automated equivalent described by the named methods; this is not a claim of a separate literal manual execution.

**Result:** PASS automated equivalent

**Evidence:** `evidence/part3-2026-11-06/regression.json` (archived)

**Exact test methods:**

- `apps.academics.test_student_management.StudentManagementTests.test_required_class_section_and_name_are_validated`

**Qualification:** Automated equivalent using isolated synthetic fixtures; literal manual example accounts and counts were not separately executed.

## UT_02_3  Verify Add student rejects a duplicate roll number, an invalid email and a class/section mismatch.

**Module:** Student Management / BL-07

**Preconditions:** Admin is logged in. Password and OTP verification are complete; any required first-login password change is complete.

**Parameters:**  Roll s001 (exists as S001); email abc; mismatched section.

**Steps:** 1: Add a student with roll number s001. 2: Add one with email 'abc'. 3: Choose class B.Tech CSE Year 2 with a section belonging to another class.

**Expected result:** 'This roll number already exists.'; 'Enter a valid email address.'; 'The section must belong to the selected dept and sem.' Nothing is saved.

**Actual result:** Fresh execution: 3 mapped test method(s) passed. Assertions cover the automated equivalent described by the named methods; this is not a claim of a separate literal manual execution.

**Result:** PASS automated equivalent

**Evidence:** `evidence/part3-2026-11-06/regression.json` (archived)

**Exact test methods:**

- `apps.academics.test_student_management.StudentManagementTests.test_duplicate_roll_is_rejected_case_insensitively`
- `apps.academics.test_student_management.StudentManagementTests.test_class_section_mismatch_is_rejected`
- `tests.test_part3_validation.TestPlanValidationTests.test_invalid_student_email_does_not_create_account_or_send_credentials`

**Qualification:** Automated equivalent using isolated synthetic fixtures; literal manual example accounts and counts were not separately executed.

## IT_02_1  Verify a new student appears in the student list and section roster and can log in.

**Module:** Student Management / BL-07

**Preconditions:** Admin is logged in. Password and OTP verification are complete; any required first-login password change is complete.

**Parameters:**  S005, 'Test Student Five', Section A.

**Steps:** 1: Add student S005 to Section A. 2: Open Manage students. 3: Enrol S005 in CS101 (Section A). 4: Log in as S005 with the temporary password.

**Expected result:** S005 is listed under Students and on the Section A CS101 roster; S005 logs in and must change the temporary password.

**Actual result:** Fresh execution: 2 mapped test method(s) passed. Assertions cover the automated equivalent described by the named methods; this is not a claim of a separate literal manual execution.

**Result:** PASS automated equivalent

**Evidence:** `evidence/part3-2026-11-06/regression.json` (archived)

**Exact test methods:**

- `apps.academics.test_student_management.StudentManagementTests.test_admin_creates_student_and_login_atomically`
- `tests.test_integration.ProvisionedAttendanceJourneyTests.test_provisioned_accounts_complete_otp_then_corrected_totals_agree_everywhere`

**Qualification:** Automated equivalent using isolated synthetic fixtures; literal manual example accounts and counts were not separately executed.

## IT_02_2  Verify only the Admin can add, update, deactivate, or delete students (AR-02).

**Module:** Student Management / BL-07

**Preconditions:** Faculty F1 (assigned to Section A) and Student S1 accounts exist.

**Parameters:**  F1 and S1 credentials; student 21CS002.

**Steps:** 1: Log in as F1 and attempt to add, update, deactivate, and delete student 21CS002. 2: Repeat each attempt as S1.

**Expected result:** Every attempt is denied with an authorization error; student 21CS002 is unchanged; each denial is logged.

**Actual result:** Fresh execution: 1 mapped test method(s) passed. Assertions cover the automated equivalent described by the named methods; this is not a claim of a separate literal manual execution.

**Result:** PASS automated equivalent

**Evidence:** `evidence/part3-2026-11-06/regression.json` (archived)

**Exact test methods:**

- `apps.academics.test_student_management.StudentManagementTests.test_faculty_scope_student_self_view_and_writes_denied`

**Qualification:** Automated equivalent using isolated synthetic fixtures; literal manual example accounts and counts were not separately executed.

## IT_02_3  Verify edited student details persist after logout and login.

**Module:** Student Management / BL-07

**Preconditions:** Admin is logged in. Password and OTP verification are complete; any required first-login password change is complete.

**Parameters:**  New name for S002.

**Steps:** 1: Edit S002's name to 'Test Student Two Updated'. 2: Log out and log in as ADMIN1. 3: Open S002.

**Expected result:** S002 shows the new name; the audit log has a student.update entry.

**Actual result:** Fresh execution: 1 mapped test method(s) passed. Assertions cover the automated equivalent described by the named methods; this is not a claim of a separate literal manual execution.

**Result:** PASS automated equivalent

**Evidence:** `evidence/part3-2026-11-06/regression.json` (archived)

**Exact test methods:**

- `apps.academics.test_student_management.StudentManagementTests.test_admin_can_edit_student_and_changes_persist`

**Qualification:** Automated equivalent using isolated synthetic fixtures; literal manual example accounts and counts were not separately executed.

## IT_02_4  Verify faculty can view only students in their assigned classes (AR-02).

**Module:** Student Management / BL-07

**Preconditions:** F1 is assigned to Section A only; S1 is in Section A; S4 is in Section B.

**Parameters:**  F1 credentials; S1 and S4.

**Steps:** 1: Log in as F1. 2: Open S1's details. 3: Open S4's details.

**Expected result:** S1's details are shown read-only; access to S4 is denied and logged.

**Actual result:** Fresh execution: 1 mapped test method(s) passed. Assertions cover the automated equivalent described by the named methods; this is not a claim of a separate literal manual execution.

**Result:** PASS automated equivalent

**Evidence:** `evidence/part3-2026-11-06/regression.json` (archived)

**Exact test methods:**

- `apps.academics.test_student_management.StudentManagementTests.test_faculty_scope_student_self_view_and_writes_denied`

**Qualification:** Automated equivalent using isolated synthetic fixtures; literal manual example accounts and counts were not separately executed.

## ST_02_1  End-to-end system test: complete the full "Manage Students" workflow as an actual user would.

**Module:** Student Management / BL-07

**Preconditions:** Admin is logged in. Password and OTP verification are complete; any required first-login password change is complete.

**Parameters:**  Roll S005, 'Test Student Five', Section A, s005@example.test.

**Steps:** 1: Admin opens the Student Management screen. 2: Admin adds a new student with roll number, name, class, and section. 3: System validates the data and checks for duplicate roll numbers. 4: System saves the student record and creates the student's login with a one-time temporary password. 5: Admin updates the student's name.

**Expected result:** The student appears in the Section A roster, can log in with the temporary password (and must change it), and the updated name is shown in all views.

**Actual result:** Fresh execution: 2 mapped test method(s) passed. Assertions cover the automated equivalent described by the named methods; this is not a claim of a separate literal manual execution.

**Result:** PASS automated equivalent

**Evidence:** `evidence/part3-2026-11-06/regression.json` (archived)

**Exact test methods:**

- `apps.academics.test_student_management.StudentManagementTests.test_admin_creates_student_and_login_atomically`
- `tests.test_integration.ProvisionedAttendanceJourneyTests.test_provisioned_accounts_complete_otp_then_corrected_totals_agree_everywhere`

**Qualification:** Automated equivalent using isolated synthetic fixtures; literal manual example accounts and counts were not separately executed.

## ST_02_2  System test: verify the exception flow  -  Duplicate roll number entered: system rejects and shows an error.

**Module:** Student Management / BL-07

**Preconditions:** Admin is logged in. Password and OTP verification are complete; any required first-login password change is complete.

**Parameters:**  Roll s001 (S001 exists).

**Steps:** 1: Open Add student. 2: Enter roll number s001. 3: Save.

**Expected result:** 'This roll number already exists.'; no second account is created.

**Actual result:** Fresh execution: 1 mapped test method(s) passed. Assertions cover the automated equivalent described by the named methods; this is not a claim of a separate literal manual execution.

**Result:** PASS automated equivalent

**Evidence:** `evidence/part3-2026-11-06/regression.json` (archived)

**Exact test methods:**

- `apps.academics.test_student_management.StudentManagementTests.test_duplicate_roll_is_rejected_case_insensitively`

**Qualification:** Automated equivalent using isolated synthetic fixtures; literal manual example accounts and counts were not separately executed.

## ST_02_3  Verify deactivating a student keeps history and removes them from new sheets (AR-03).

**Module:** Student Management / BL-07

**Preconditions:** Admin is logged in; S1 has attendance in CS101. Password and OTP verification are complete; any required first-login password change is complete.

**Parameters:**  Student S1.

**Steps:** 1: Deactivate S1. 2: As F1, open a new CS101 sheet for Section A. 3: Open S1's attendance history. 4: Try to log in as S1.

**Expected result:** S1 is not on the new sheet; S1's past records remain, labelled "Inactive"; S1's login is blocked; the deactivation is logged.

**Actual result:** Fresh execution: 2 mapped test method(s) passed. Assertions cover the automated equivalent described by the named methods; this is not a claim of a separate literal manual execution.

**Result:** PASS automated equivalent

**Evidence:** `evidence/part3-2026-11-06/regression.json` (archived)

**Exact test methods:**

- `apps.academics.test_student_management.StudentManagementTests.test_deactivate_and_reactivate_keep_attendance_history`
- `apps.academics.test_student_management.StudentManagementTests.test_deactivation_keeps_recorded_attendance`

**Qualification:** Automated equivalent using isolated synthetic fixtures; literal manual example accounts and counts were not separately executed.

## ST_02_4  Verify reactivating a student restores access from the reactivation date (AR-03).

**Module:** Student Management / BL-07

**Preconditions:** S1 was deactivated on 10 Oct and reactivated on 14 Oct.

**Parameters:**  Sessions on 11 Oct and 13 Oct held while S1 was deactivated.

**Steps:** 1: As F1, open a CS101 sheet dated 14 Oct. 2: View S1's CS101 counts.

**Expected result:** S1 appears on the 14 Oct sheet; the 11 Oct and 13 Oct sessions are not counted in S1's attended/held figures; the reactivation is logged.

**Actual result:** Fresh execution: 2 mapped test method(s) passed. Assertions cover the automated equivalent described by the named methods; this is not a claim of a separate literal manual execution.

**Result:** PASS automated equivalent

**Evidence:** `evidence/part3-2026-11-06/regression.json` (archived)

**Exact test methods:**

- `apps.academics.test_student_management.StudentManagementTests.test_deactivate_and_reactivate_keep_attendance_history`
- `apps.academics.test_student_management.StudentManagementTests.test_deactivation_keeps_recorded_attendance`

**Qualification:** Automated equivalent using isolated synthetic fixtures; literal manual example accounts and counts were not separately executed.

## ST_02_5  Verify an Admin can permanently delete a student with a reason (AR-04).

**Module:** Student Management / BL-07

**Preconditions:** Admin is logged in; S5 has 4 attendance records. Password and OTP verification are complete; any required first-login password change is complete.

**Parameters:**  Student S5; reason "Duplicate record".

**Steps:** 1: Choose Delete permanently for S5. 2: Read the summary of what will be removed. 3: Enter a reason and confirm.

**Expected result:** The summary lists S5's profile, login, and 4 attendance records; after confirmation they are removed; earlier audit entries remain; the deletion is logged with the reason.

**Actual result:** Fresh execution: 1 mapped test method(s) passed. Assertions cover the automated equivalent described by the named methods; this is not a claim of a separate literal manual execution.

**Result:** PASS automated equivalent

**Evidence:** `evidence/part3-2026-11-06/regression.json` (archived)

**Exact test methods:**

- `apps.academics.test_student_management.StudentManagementTests.test_deletion_removes_attendance_but_keeps_audit`

**Qualification:** Automated equivalent using isolated synthetic fixtures; literal manual example accounts and counts were not separately executed.

## ST_02_6  Verify a permanent deletion is not made without confirmation and a reason (AR-04).

**Module:** Student Management / BL-07

**Preconditions:** Admin is logged in; student S6 exists. Password and OTP verification are complete; any required first-login password change is complete.

**Parameters:**  Student S6.

**Steps:** 1: Choose Delete permanently for S6 and leave the reason blank. 2: Repeat with a reason but click Cancel.

**Expected result:** Step 1 is rejected with "Reason is required"; step 2 makes no change; S6 still exists.

**Actual result:** Fresh execution: 1 mapped test method(s) passed. Assertions cover the automated equivalent described by the named methods; this is not a claim of a separate literal manual execution.

**Result:** PASS automated equivalent

**Evidence:** `evidence/part3-2026-11-06/regression.json` (archived)

**Exact test methods:**

- `apps.academics.test_student_management.StudentManagementTests.test_delete_needs_reason_and_retains_audit`

**Qualification:** Automated equivalent using isolated synthetic fixtures; literal manual example accounts and counts were not separately executed.

## UT_03_1  Verify Manage Faculty succeeds with valid input.

**Module:** Faculty Management / BL-08

**Preconditions:** Admin is logged in. Password and OTP verification are complete; any required first-login password change is complete.

**Parameters:**  Faculty ID f004, 'Dr. Test Four', CSE, f004@example.test.

**Steps:** 1: Admin opens the Faculty Management screen. 2: Admin adds a new faculty member with ID, name, and department. 3: System validates and saves the faculty record and creates the login.

**Expected result:** Faculty record and login are saved. The username, temporary password and login link are emailed only to that faculty member; the Admin sees masked delivery status (BL-34).

**Actual result:** Fresh execution: 1 mapped test method(s) passed. Assertions cover the automated equivalent described by the named methods; this is not a claim of a separate literal manual execution.

**Result:** PASS automated equivalent

**Evidence:** `evidence/part3-2026-11-06/regression.json` (archived)

**Exact test methods:**

- `apps.accounts.test_credential_email.CredentialEmailTests.test_faculty_creation_emails_only_owner`

**Qualification:** Automated equivalent using isolated synthetic fixtures; literal manual example accounts and counts were not separately executed.

## UT_03_2  Verify Add faculty rejects blank required fields.

**Module:** Faculty Management / BL-08

**Preconditions:** Admin is logged in. Password and OTP verification are complete; any required first-login password change is complete.

**Parameters:**  All fields blank.

**Steps:** 1: Open Manage faculty  >  Add faculty. 2: Leave all fields empty. 3: Save.

**Expected result:** 'This field is required.' under each field; no faculty member or account is created.

**Actual result:** Fresh execution: 1 mapped test method(s) passed. Assertions cover the automated equivalent described by the named methods; this is not a claim of a separate literal manual execution.

**Result:** PASS automated equivalent

**Evidence:** `evidence/part3-2026-11-06/regression.json` (archived)

**Exact test methods:**

- `apps.academics.test_faculty_management.CreateAndViewTests.test_required_fields_are_validated`

**Qualification:** Automated equivalent using isolated synthetic fixtures; literal manual example accounts and counts were not separately executed.

## UT_03_3  Verify Add faculty rejects a duplicate faculty ID, an ID used by a student, and an invalid email.

**Module:** Faculty Management / BL-08

**Preconditions:** Admin is logged in. Password and OTP verification are complete; any required first-login password change is complete.

**Parameters:**  f001 (exists); s001 (a student username); abc.

**Steps:** 1: Add faculty ID f001. 2: Add faculty ID s001. 3: Add a faculty member with email 'abc'.

**Expected result:** 'This faculty ID already exists.' for steps 1 and 2; 'Enter a valid email address.' for step 3; nothing is saved.

**Actual result:** Fresh execution: 2 mapped test method(s) passed. Assertions cover the automated equivalent described by the named methods; this is not a claim of a separate literal manual execution.

**Result:** PASS automated equivalent

**Evidence:** `evidence/part3-2026-11-06/regression.json` (archived)

**Exact test methods:**

- `apps.academics.test_faculty_management.CreateAndViewTests.test_duplicate_faculty_id_is_rejected_ignoring_case`
- `apps.academics.test_faculty_management.CreateAndViewTests.test_faculty_id_cannot_reuse_an_existing_username`

**Qualification:** Automated equivalent using isolated synthetic fixtures; literal manual example accounts and counts were not separately executed.

## IT_03_1  Verify a new faculty member can be given a class and then sees it.

**Module:** Faculty Management / BL-08

**Preconditions:** Admin is logged in. Password and OTP verification are complete; any required first-login password change is complete.

**Parameters:**  F004; MA101 in Section B.

**Steps:** 1: Add faculty F004. 2: Open Section B  >  Change teacher for MA101  >  F004. 3: Log in as F004 (after changing the password) and open My classes.

**Expected result:** F004 appears in the teacher list; Section B shows MA101 taught by F004; F004's My classes lists MA101 in B.Tech CSE Year 2 B with 2 students.

**Actual result:** Fresh execution: 2 mapped test method(s) passed. Assertions cover the automated equivalent described by the named methods; this is not a claim of a separate literal manual execution.

**Result:** PASS automated equivalent

**Evidence:** `evidence/part3-2026-11-06/regression.json` (archived)

**Exact test methods:**

- `apps.academics.test_faculty_management.CreateAndViewTests.test_admin_adds_faculty_with_login_and_temporary_password`
- `apps.academics.test_teaching_assignments.TeachingAssignmentTests.test_admin_links_faculty_and_subject_to_section`

**Qualification:** Automated equivalent using isolated synthetic fixtures; literal manual example accounts and counts were not separately executed.

## IT_03_2  Verify only the Admin can manage faculty (SEC-14).

**Module:** Faculty Management / BL-08

**Preconditions:** F001 and S001 are logged in (separate browsers). Password and OTP verification are complete; any required first-login password change is complete.

**Parameters:**  F001 and S001 credentials; target F003.

**Steps:** 1: As F001, open /faculty/ and try to deactivate F003. 2: Repeat as S001.

**Expected result:** Every request shows 'Access denied'; F003 stays active; the denials are logged.

**Actual result:** Fresh execution: 1 mapped test method(s) passed. Assertions cover the automated equivalent described by the named methods; this is not a claim of a separate literal manual execution.

**Result:** PASS automated equivalent

**Evidence:** `evidence/part3-2026-11-06/regression.json` (archived)

**Exact test methods:**

- `apps.academics.test_faculty_management.PermissionTests.test_non_admins_cannot_manage_faculty`

**Qualification:** Automated equivalent using isolated synthetic fixtures; literal manual example accounts and counts were not separately executed.

## IT_03_3  Verify edited faculty details persist after logout and login.

**Module:** Faculty Management / BL-08

**Preconditions:** Admin is logged in. Password and OTP verification are complete; any required first-login password change is complete.

**Parameters:**  F003 department ECE.

**Steps:** 1: Change F003's department to ECE. 2: Log out and log in as ADMIN1. 3: Open F003.

**Expected result:** F003 shows department ECE; the audit log has faculty.update with old CSE and new ECE.

**Actual result:** Fresh execution: 1 mapped test method(s) passed. Assertions cover the automated equivalent described by the named methods; this is not a claim of a separate literal manual execution.

**Result:** PASS automated equivalent

**Evidence:** `evidence/part3-2026-11-06/regression.json` (archived)

**Exact test methods:**

- `apps.academics.test_faculty_management.EditTests.test_admin_updates_details_and_change_persists`

**Qualification:** Automated equivalent using isolated synthetic fixtures; literal manual example accounts and counts were not separately executed.

## ST_03_1  End-to-end system test: complete the full "Manage Faculty" workflow as an actual user would.

**Module:** Faculty Management / BL-08

**Preconditions:** Admin is logged in. Password and OTP verification are complete; any required first-login password change is complete.

**Parameters:**  Faculty ID f004, 'Dr. Test Four', CSE; then make F004 the teacher of MA101 in Section B.

**Steps:** 1: Admin opens the Faculty Management screen. 2: Admin adds a new faculty member with ID, name, and department. 3: System validates and saves the faculty record and creates the login. 4: Admin updates the faculty record. 5: Admin assigns faculty to subjects/classes.

**Expected result:** F004 is created with a temporary password, edited, and shown as MA101's teacher on the Section B page; every step is in the audit log.

**Actual result:** Fresh execution: 2 mapped test method(s) passed. Assertions cover the automated equivalent described by the named methods; this is not a claim of a separate literal manual execution.

**Result:** PASS automated equivalent

**Evidence:** `evidence/part3-2026-11-06/regression.json` (archived)

**Exact test methods:**

- `apps.academics.test_faculty_management.CreateAndViewTests.test_admin_adds_faculty_with_login_and_temporary_password`
- `apps.academics.test_teaching_assignments.TeachingAssignmentTests.test_admin_links_faculty_and_subject_to_section`

**Qualification:** Automated equivalent using isolated synthetic fixtures; literal manual example accounts and counts were not separately executed.

## ST_03_2  System test: verify the exception flow  -  Duplicate faculty ID entered: system rejects the entry.

**Module:** Faculty Management / BL-08

**Preconditions:** Admin is logged in. Password and OTP verification are complete; any required first-login password change is complete.

**Parameters:**  f001 (F001 exists).

**Steps:** 1: Open Add faculty. 2: Enter faculty ID f001. 3: Save.

**Expected result:** 'This faculty ID already exists.'; no second account is created.

**Actual result:** Fresh execution: 1 mapped test method(s) passed. Assertions cover the automated equivalent described by the named methods; this is not a claim of a separate literal manual execution.

**Result:** PASS automated equivalent

**Evidence:** `evidence/part3-2026-11-06/regression.json` (archived)

**Exact test methods:**

- `apps.academics.test_faculty_management.CreateAndViewTests.test_duplicate_faculty_id_is_rejected_ignoring_case`

**Qualification:** Automated equivalent using isolated synthetic fixtures; literal manual example accounts and counts were not separately executed.

## ST_03_3  Verify a faculty member with active class assignments cannot be deactivated or deleted (AR-03, AR-04).

**Module:** Faculty Management / BL-08

**Preconditions:** F1 is assigned to Section A, CS101.

**Parameters:**  Faculty F1.

**Steps:** 1: Try to deactivate F1. 2: Try to permanently delete F1.

**Expected result:** Both actions are blocked; the message lists F1's active assignments; F1 is unchanged.

**Actual result:** Fresh execution: 2 mapped test method(s) passed. Assertions cover the automated equivalent described by the named methods; this is not a claim of a separate literal manual execution.

**Result:** PASS automated equivalent

**Evidence:** `evidence/part3-2026-11-06/regression.json` (archived)

**Exact test methods:**

- `apps.academics.test_faculty_management.DeactivateAndDeleteTests.test_faculty_with_classes_cannot_be_deactivated`
- `apps.academics.test_faculty_management.DeactivateAndDeleteTests.test_faculty_with_classes_cannot_be_deleted`

**Qualification:** Automated equivalent using isolated synthetic fixtures; literal manual example accounts and counts were not separately executed.

## ST_03_4  Verify permanently deleting an unassigned faculty member keeps the attendance they recorded (AR-04).

**Module:** Faculty Management / BL-08

**Preconditions:** F3 has no active assignments and recorded the 6 Oct CS101 session.

**Parameters:**  Faculty F3; reason "Left the institution".

**Steps:** 1: Permanently delete F3 with a reason. 2: Open the 6 Oct CS101 session.

**Expected result:** F3's profile and login are removed; the 6 Oct session and its records remain, showing F3's faculty ID as the recorder; the deletion is logged.

**Actual result:** Fresh execution: 1 mapped test method(s) passed. Assertions cover the automated equivalent described by the named methods; this is not a claim of a separate literal manual execution.

**Result:** PASS automated equivalent

**Evidence:** `evidence/part3-2026-11-06/regression.json` (archived)

**Exact test methods:**

- `apps.academics.test_faculty_management.DeactivateAndDeleteTests.test_delete_keeps_attendance_they_recorded`

**Qualification:** Automated equivalent using isolated synthetic fixtures; literal manual example accounts and counts were not separately executed.

## ST_03_5  Verify a reactivated faculty member can log in again (AR-03).

**Module:** Faculty Management / BL-08

**Preconditions:** F4 was deactivated.

**Parameters:**  Faculty F4.

**Steps:** 1: Reactivate F4. 2: Log in as F4.

**Expected result:** Login succeeds; the reactivation is logged.

**Actual result:** Fresh execution: 1 mapped test method(s) passed. Assertions cover the automated equivalent described by the named methods; this is not a claim of a separate literal manual execution.

**Result:** PASS automated equivalent

**Evidence:** `evidence/part3-2026-11-06/regression.json` (archived)

**Exact test methods:**

- `apps.academics.test_faculty_management.DeactivateAndDeleteTests.test_deactivated_faculty_cannot_log_in_and_reactivation_restores_access`

**Qualification:** Automated equivalent using isolated synthetic fixtures; literal manual example accounts and counts were not separately executed.

## UT_04_1  Verify Manage Courses/Subjects succeeds with valid input.

**Module:** Course Management / BL-09

**Preconditions:** User is logged in with sufficient privileges. Password and OTP verification are complete; any required first-login password change is complete.

**Parameters:**  Code ph101, name Physics (as ADMIN1).

**Steps:** 1: User opens the Course Management screen. 2: User creates a new subject with a subject code and name. 3: System validates the subject code is unique.

**Expected result:** Subject PH101 - Physics is saved (code stored in capitals) and its details page opens.

**Actual result:** Fresh execution: 1 mapped test method(s) passed. Assertions cover the automated equivalent described by the named methods; this is not a claim of a separate literal manual execution.

**Result:** PASS automated equivalent

**Evidence:** `evidence/part3-2026-11-06/regression.json` (archived)

**Exact test methods:**

- `apps.academics.test_subject_management.CreateAndViewTests.test_admin_creates_subject_code_stored_in_capitals`

**Qualification:** Automated equivalent using isolated synthetic fixtures; literal manual example accounts and counts were not separately executed.

## UT_04_2  Verify Add subject rejects blank fields.

**Module:** Course Management / BL-09

**Preconditions:** User is logged in with sufficient privileges. Password and OTP verification are complete; any required first-login password change is complete.

**Parameters:**  Blank code and name.

**Steps:** 1: Open Subjects  >  Add subject. 2: Leave code and name blank. 3: Save.

**Expected result:** 'This field is required.' under both fields; no subject is created.

**Actual result:** Fresh execution: 2 mapped test method(s) passed. Assertions cover the automated equivalent described by the named methods; this is not a claim of a separate literal manual execution.

**Result:** PASS automated equivalent

**Evidence:** `evidence/part3-2026-11-06/regression.json` (archived)

**Exact test methods:**

- `apps.academics.test_subject_management.CreateAndViewTests.test_missing_and_invalid_details_are_rejected`
- `apps.academics.test_subject_management.CreateAndViewTests.test_duplicate_code_is_rejected_ignoring_case`

**Qualification:** Automated equivalent using isolated synthetic fixtures; literal manual example accounts and counts were not separately executed.

## UT_04_3  Verify Add subject rejects a duplicate code and invalid characters.

**Module:** Course Management / BL-09

**Preconditions:** User is logged in with sufficient privileges. Password and OTP verification are complete; any required first-login password change is complete.

**Parameters:**  cs101 (exists); 'CS 1!'.

**Steps:** 1: Add code cs101. 2: Add code 'CS 1!'.

**Expected result:** 'A subject with this code already exists.'; 'Use letters, digits and hyphens only.'; nothing is saved.

**Actual result:** Fresh execution: 2 mapped test method(s) passed. Assertions cover the automated equivalent described by the named methods; this is not a claim of a separate literal manual execution.

**Result:** PASS automated equivalent

**Evidence:** `evidence/part3-2026-11-06/regression.json` (archived)

**Exact test methods:**

- `apps.academics.test_subject_management.CreateAndViewTests.test_missing_and_invalid_details_are_rejected`
- `apps.academics.test_subject_management.CreateAndViewTests.test_duplicate_code_is_rejected_ignoring_case`

**Qualification:** Automated equivalent using isolated synthetic fixtures; literal manual example accounts and counts were not separately executed.

## IT_04_1  Verify a new subject can be offered in a section and students enrolled in it.

**Module:** Course Management / BL-09

**Preconditions:** User is logged in with sufficient privileges. Password and OTP verification are complete; any required first-login password change is complete.

**Parameters:**  PH101; Section A; F001; S002.

**Steps:** 1: Add PH101. 2: Section A  >  Add subject: PH101, teacher F001. 3: Enrol S002 in PH101.

**Expected result:** Section A lists PH101 taught by F001; S002's profile lists PH101 in Section A; F001's My classes includes PH101.

**Actual result:** Fresh execution: 3 mapped test method(s) passed. Assertions cover the automated equivalent described by the named methods; this is not a claim of a separate literal manual execution.

**Result:** PASS automated equivalent

**Evidence:** `evidence/part3-2026-11-06/regression.json` (archived)

**Exact test methods:**

- `apps.academics.test_subject_management.OfferInSectionTests.test_admin_offers_subject_in_section_without_faculty_yet`
- `apps.academics.test_section_enrollment.SectionEnrollmentTests.test_admin_enrolls_student_and_sees_roster`
- `apps.academics.test_subject_management.EditTests.test_admin_renames_subject_and_change_persists`

**Qualification:** Automated equivalent using isolated synthetic fixtures; literal manual example accounts and counts were not separately executed.

## IT_04_2  Verify Students cannot manage subjects and Faculty cannot delete subjects or edit ones they do not teach.

**Module:** Course Management / BL-09

**Preconditions:** S001 and F001 are logged in (separate browsers). Password and OTP verification are complete; any required first-login password change is complete.

**Parameters:**  S001, F001; MA101 (taught by F002).

**Steps:** 1: As S001, open /subjects/. 2: As F001, try to delete MA101 and to edit MA101's name.

**Expected result:** Every request shows 'Access denied'; MA101 is unchanged.

**Actual result:** Fresh execution: 3 mapped test method(s) passed. Assertions cover the automated equivalent described by the named methods; this is not a claim of a separate literal manual execution.

**Result:** PASS automated equivalent

**Evidence:** `evidence/part3-2026-11-06/regression.json` (archived)

**Exact test methods:**

- `apps.academics.test_subject_management.CreateAndViewTests.test_student_cannot_view_or_create_subjects`
- `apps.academics.test_subject_management.DeleteTests.test_only_admin_can_delete`
- `apps.academics.test_subject_management.EditTests.test_faculty_edits_only_subjects_they_teach`

**Qualification:** Automated equivalent using isolated synthetic fixtures; literal manual example accounts and counts were not separately executed.

## IT_04_3  Verify a renamed subject persists after logout and login.

**Module:** Course Management / BL-09

**Preconditions:** User is logged in with sufficient privileges. Password and OTP verification are complete; any required first-login password change is complete.

**Parameters:**  New name 'Mathematics I'.

**Steps:** 1: Rename MA101 to 'Mathematics I'. 2: Log out and log in. 3: Open MA101.

**Expected result:** MA101 shows 'Mathematics I'; the code stays MA101; subject.update is logged.

**Actual result:** Fresh execution: 2 mapped test method(s) passed. Assertions cover the automated equivalent described by the named methods; this is not a claim of a separate literal manual execution.

**Result:** PASS automated equivalent

**Evidence:** `evidence/part3-2026-11-06/regression.json` (archived)

**Exact test methods:**

- `apps.academics.test_subject_management.EditTests.test_admin_renames_subject_and_change_persists`
- `apps.academics.test_subject_management.EditTests.test_code_cannot_be_changed`

**Qualification:** Automated equivalent using isolated synthetic fixtures; literal manual example accounts and counts were not separately executed.

## ST_04_1  End-to-end system test: complete the full "Manage Courses/Subjects" workflow as an actual user would.

**Module:** Course Management / BL-09

**Preconditions:** User is logged in with sufficient privileges. Password and OTP verification are complete; any required first-login password change is complete.

**Parameters:**  PH101 Physics; offer in Section A; rename to 'Physics I'.

**Steps:** 1: User opens the Course Management screen. 2: User creates a new subject with a subject code and name. 3: System validates the subject code is unique. 4: System saves the subject and links it to a class/section.

**Expected result:** PH101 is created, offered in Section A ('No teacher assigned' until one is set) and renamed; every step is in the audit log.

**Actual result:** Fresh execution: 3 mapped test method(s) passed. Assertions cover the automated equivalent described by the named methods; this is not a claim of a separate literal manual execution.

**Result:** PASS automated equivalent

**Evidence:** `evidence/part3-2026-11-06/regression.json` (archived)

**Exact test methods:**

- `apps.academics.test_subject_management.OfferInSectionTests.test_admin_offers_subject_in_section_without_faculty_yet`
- `apps.academics.test_section_enrollment.SectionEnrollmentTests.test_admin_enrolls_student_and_sees_roster`
- `apps.academics.test_subject_management.EditTests.test_admin_renames_subject_and_change_persists`

**Qualification:** Automated equivalent using isolated synthetic fixtures; literal manual example accounts and counts were not separately executed.

## ST_04_2  System test: verify the exception flow  -  Duplicate subject code entered: system rejects the entry.

**Module:** Course Management / BL-09

**Preconditions:** User is logged in with sufficient privileges. Password and OTP verification are complete; any required first-login password change is complete.

**Parameters:**  cs101 (CS101 exists).

**Steps:** 1: Open Add subject. 2: Enter code cs101. 3: Save.

**Expected result:** 'A subject with this code already exists.'; no subject is created.

**Actual result:** Fresh execution: 1 mapped test method(s) passed. Assertions cover the automated equivalent described by the named methods; this is not a claim of a separate literal manual execution.

**Result:** PASS automated equivalent

**Evidence:** `evidence/part3-2026-11-06/regression.json` (archived)

**Exact test methods:**

- `apps.academics.test_subject_management.CreateAndViewTests.test_duplicate_code_is_rejected_ignoring_case`

**Qualification:** Automated equivalent using isolated synthetic fixtures; literal manual example accounts and counts were not separately executed.

## ST_04_3  Verify a subject with attendance records cannot be deleted (UC-04 4a).

**Module:** Course Management / BL-09

**Preconditions:** CS101 has attendance records.

**Parameters:**  Subject CS101.

**Steps:** 1: Try to delete CS101.

**Expected result:** Deletion is blocked with a message; CS101 and its records remain.

**Actual result:** Fresh execution: 2 mapped test method(s) passed. Assertions cover the automated equivalent described by the named methods; this is not a claim of a separate literal manual execution.

**Result:** PASS automated equivalent

**Evidence:** `evidence/part3-2026-11-06/regression.json` (archived)

**Exact test methods:**

- `apps.academics.test_subject_management.DeleteTests.test_subject_with_attendance_cannot_be_deleted`
- `apps.attendance.tests.AttendanceTests.test_subject_with_attendance_cannot_be_deleted`

**Qualification:** Automated equivalent using isolated synthetic fixtures; literal manual example accounts and counts were not separately executed.

## ST_04_4  Verify a subject without attendance records can be deleted.

**Module:** Course Management / BL-09

**Preconditions:** CS999 has no attendance records.

**Parameters:**  Subject CS999.

**Steps:** 1: Delete CS999.

**Expected result:** CS999 is deleted and no longer appears in subject lists.

**Actual result:** Fresh execution: 1 mapped test method(s) passed. Assertions cover the automated equivalent described by the named methods; this is not a claim of a separate literal manual execution.

**Result:** PASS automated equivalent

**Evidence:** `evidence/part3-2026-11-06/regression.json` (archived)

**Exact test methods:**

- `apps.academics.test_subject_management.DeleteTests.test_unused_subject_is_deleted_with_its_offerings`

**Qualification:** Automated equivalent using isolated synthetic fixtures; literal manual example accounts and counts were not separately executed.

## UT_05_1  Verify Manage Classes/Sections succeeds with valid input.

**Module:** Class Management / BL-10, BL-11

**Preconditions:** Admin is logged in. Password and OTP verification are complete; any required first-login password change is complete.

**Parameters:**  Class 'B.Tech CSE Year 2', section c.

**Steps:** 1: Admin opens the Class/Section Management screen. 2: Admin creates a new class/section. 3: Admin assigns enrolled students to the section.

**Expected result:** Section 'B.Tech CSE Year 2 C' is created (section name stored in capitals) and its page opens.

**Actual result:** Fresh execution: 1 mapped test method(s) passed. Assertions cover the automated equivalent described by the named methods; this is not a claim of a separate literal manual execution.

**Result:** PASS automated equivalent

**Evidence:** `evidence/part3-2026-11-06/regression.json` (archived)

**Exact test methods:**

- `apps.academics.test_section_enrollment.SectionEnrollmentTests.test_admin_can_create_and_view_sections`

**Qualification:** Automated equivalent using isolated synthetic fixtures; literal manual example accounts and counts were not separately executed.

## UT_05_2  Verify Create section rejects blank fields.

**Module:** Class Management / BL-10, BL-11

**Preconditions:** Admin is logged in. Password and OTP verification are complete; any required first-login password change is complete.

**Parameters:**  Blank class and section.

**Steps:** 1: Open Manage classes, sections and enrollment  >  Create. 2: Leave class and section blank. 3: Save.

**Expected result:** Blank Dept and sem or Section produces required-field errors and creates no section. Batch year is optional.

**Actual result:** Fresh execution: 1 mapped test method(s) passed. Assertions cover the automated equivalent described by the named methods; this is not a claim of a separate literal manual execution.

**Result:** PASS automated equivalent

**Evidence:** `evidence/part3-2026-11-06/regression.json` (archived)

**Exact test methods:**

- `tests.test_part3_validation.TestPlanValidationTests.test_blank_required_section_fields_do_not_create_section`

**Qualification:** Automated equivalent using isolated synthetic fixtures; literal manual example accounts and counts were not separately executed.

## UT_05_3  Verify a duplicate section is rejected regardless of letter case.

**Module:** Class Management / BL-10, BL-11

**Preconditions:** Admin is logged in. Password and OTP verification are complete; any required first-login password change is complete.

**Parameters:**  Duplicate of Section A in lower case.

**Steps:** 1: Create class 'b.tech cse year 2', section 'a'.

**Expected result:** 'That section already exists in this class.'; only one Section A exists.

**Actual result:** Fresh execution: 1 mapped test method(s) passed. Assertions cover the automated equivalent described by the named methods; this is not a claim of a separate literal manual execution.

**Result:** PASS automated equivalent

**Evidence:** `evidence/part3-2026-11-06/regression.json` (archived)

**Exact test methods:**

- `apps.academics.test_section_enrollment.SectionEnrollmentTests.test_duplicate_section_is_rejected`

**Qualification:** Automated equivalent using isolated synthetic fixtures; literal manual example accounts and counts were not separately executed.

## IT_05_1  Verify a teaching assignment controls which faculty member can see and mark a class (BL-11).

**Module:** Class Management / BL-10, BL-11

**Preconditions:** Admin is logged in. Password and OTP verification are complete; any required first-login password change is complete.

**Parameters:**  CS101 in Section A; teacher F001  >  F003.

**Steps:** 1: In Section A, Change teacher for CS101 from F001 to F003. 2: Log in as F003  >  My classes and Mark attendance. 3: Log in as F001  >  My classes.

**Expected result:** F003 sees CS101 in Section A with 3 students and can load its roster; F001 no longer sees it, and requesting it directly shows 'Access denied'.

**Actual result:** Fresh execution: 1 mapped test method(s) passed. Assertions cover the automated equivalent described by the named methods; this is not a claim of a separate literal manual execution.

**Result:** PASS automated equivalent

**Evidence:** `evidence/part3-2026-11-06/regression.json` (archived)

**Exact test methods:**

- `apps.academics.test_teaching_assignments.TeachingAssignmentTests.test_changing_teacher_moves_attendance_access`

**Qualification:** Automated equivalent using isolated synthetic fixtures; literal manual example accounts and counts were not separately executed.

## IT_05_2  Verify only the Admin can create sections, enrol students and assign teachers (SEC-14).

**Module:** Class Management / BL-10, BL-11

**Preconditions:** F001 and S001 are logged in (separate browsers). Password and OTP verification are complete; any required first-login password change is complete.

**Parameters:**  F001 and S001 credentials.

**Steps:** 1: As F001, open /sections/ and try Add subject in Section A. 2: Repeat as S001.

**Expected result:** Every request shows 'Access denied'; no section, enrollment or assignment changes.

**Actual result:** Fresh execution: 2 mapped test method(s) passed. Assertions cover the automated equivalent described by the named methods; this is not a claim of a separate literal manual execution.

**Result:** PASS automated equivalent

**Evidence:** `evidence/part3-2026-11-06/regression.json` (archived)

**Exact test methods:**

- `apps.academics.test_section_enrollment.SectionEnrollmentTests.test_faculty_and_student_cannot_manage_sections_or_enrollment`
- `apps.academics.test_teaching_assignments.TeachingAssignmentTests.test_non_admins_cannot_assign_or_change_teachers`

**Qualification:** Automated equivalent using isolated synthetic fixtures; literal manual example accounts and counts were not separately executed.

## IT_05_3  Verify an enrollment persists after logout and login.

**Module:** Class Management / BL-10, BL-11

**Preconditions:** Admin is logged in. Password and OTP verification are complete; any required first-login password change is complete.

**Parameters:**  S003  >  CS101, Section A.

**Steps:** 1: Enrol S003 in CS101 in Section A. 2: Log out and log in as ADMIN1. 3: Open Section A.

**Expected result:** Section A's CS101 roster lists S003 as Active; enrollment.create is logged.

**Actual result:** Fresh execution: 2 mapped test method(s) passed. Assertions cover the automated equivalent described by the named methods; this is not a claim of a separate literal manual execution.

**Result:** PASS automated equivalent

**Evidence:** `evidence/part3-2026-11-06/regression.json` (archived)

**Exact test methods:**

- `apps.academics.test_teaching_assignments.TeachingAssignmentTests.test_assignment_persists_after_logout_and_login`
- `apps.academics.test_section_enrollment.SectionEnrollmentTests.test_admin_enrolls_student_and_sees_roster`

**Qualification:** Automated equivalent using isolated synthetic fixtures; literal manual example accounts and counts were not separately executed.

## ST_05_1  End-to-end system test: complete the full "Manage Classes/Sections" workflow as an actual user would.

**Module:** Class Management / BL-10, BL-11

**Preconditions:** Admin is logged in. Password and OTP verification are complete; any required first-login password change is complete.

**Parameters:**  New Section C; Add subject PH101 with teacher F003; enrol S004 in PH101.

**Steps:** 1: Admin opens the Class/Section Management screen. 2: Admin creates a new class/section. 3: Admin assigns enrolled students to the section. 4: Admin assigns a faculty member and subjects to the section. 5: System saves the class configuration.

**Expected result:** Section C shows PH101 taught by F003 with S004 on its roster; F003's My classes lists it; every step is logged.

**Actual result:** Fresh execution: 3 mapped test method(s) passed. Assertions cover the automated equivalent described by the named methods; this is not a claim of a separate literal manual execution.

**Result:** PASS automated equivalent

**Evidence:** `evidence/part3-2026-11-06/regression.json` (archived)

**Exact test methods:**

- `apps.academics.test_section_enrollment.SectionEnrollmentTests.test_admin_can_create_and_view_sections`
- `apps.academics.test_teaching_assignments.TeachingAssignmentTests.test_admin_links_faculty_and_subject_to_section`
- `apps.academics.test_section_enrollment.SectionEnrollmentTests.test_admin_enrolls_student_and_sees_roster`

**Qualification:** Automated equivalent using isolated synthetic fixtures; literal manual example accounts and counts were not separately executed.

## ST_05_2  System test: verify the exception flow  -  Student assigned to a second section for the same subject: system rejects the assignment.

**Module:** Class Management / BL-10, BL-11

**Preconditions:** Admin is logged in. Password and OTP verification are complete; any required first-login password change is complete.

**Parameters:**  Student S1; Sections A and B both include CS101.

**Steps:** 1: Enrol S1 in Section A, which has CS101. 2: Assign S1 to Section B, which also has CS101. 3: Save.

**Expected result:** The assignment is rejected with a message naming Section A; S1 remains only in Section A.

**Actual result:** Fresh execution: 1 mapped test method(s) passed. Assertions cover the automated equivalent described by the named methods; this is not a claim of a separate literal manual execution.

**Result:** PASS automated equivalent

**Evidence:** `evidence/part3-2026-11-06/regression.json` (archived)

**Exact test methods:**

- `apps.academics.test_section_enrollment.SectionEnrollmentTests.test_second_section_for_same_subject_is_rejected_with_existing_section`

**Qualification:** Automated equivalent using isolated synthetic fixtures; literal manual example accounts and counts were not separately executed.

## UT_06_1  Verify Mark Attendance succeeds with valid input.

**Module:** Attendance Marking / BL-12, BL-13

**Preconditions:** Faculty is logged in and is assigned to the selected section and subject. Password and OTP verification are complete; any required first-login password change is complete.

**Parameters:**  Section A, subject CS101, today, period 1; S1 Present, S2 Absent, S3 Present.

**Steps:** 1: Faculty selects the class/section, subject, date, and period. 2: System displays the enrolled, active student list. 3: Faculty marks each student Present or Absent and submits.

**Expected result:** The session is saved with exactly one record per student (S1 Present, S2 Absent, S3 Present) and a confirmation is shown.

**Actual result:** Fresh execution: 1 mapped test method(s) passed. Assertions cover the automated equivalent described by the named methods; this is not a claim of a separate literal manual execution.

**Result:** PASS automated equivalent

**Evidence:** `evidence/part3-2026-11-06/regression.json` (archived)

**Exact test methods:**

- `apps.attendance.test_marking.MarkingTests.test_saves_all_records_and_survives_relogin`

**Qualification:** Automated equivalent using isolated synthetic fixtures; literal manual example accounts and counts were not separately executed.

## UT_06_2  Verify a submission with an unmarked student is rejected (AR-07).

**Module:** Attendance Marking / BL-12, BL-13

**Preconditions:** Faculty is logged in and is assigned to the selected section and subject. Password and OTP verification are complete; any required first-login password change is complete.

**Parameters:**  S3 left unmarked.

**Steps:** 1: Open the sheet for Section A, CS101, today, period 1. 2: Mark S1 and S2; leave S3 unmarked. 3: Submit.

**Expected result:** Submission is rejected; S3 is highlighted; no record is saved for the session.

**Actual result:** Fresh execution: 1 mapped test method(s) passed. Assertions cover the automated equivalent described by the named methods; this is not a claim of a separate literal manual execution.

**Result:** PASS automated equivalent

**Evidence:** `evidence/part3-2026-11-06/regression.json` (archived)

**Exact test methods:**

- `apps.attendance.test_marking.MarkingTests.test_missing_student_is_rejected_without_partial_save`

**Qualification:** Automated equivalent using isolated synthetic fixtures; literal manual example accounts and counts were not separately executed.

## UT_06_3  Verify invalid statuses and future dates are rejected (AR-05, AR-06).

**Module:** Attendance Marking / BL-12, BL-13

**Preconditions:** Faculty is logged in and is assigned to the selected section and subject. Password and OTP verification are complete; any required first-login password change is complete.

**Parameters:**  Status "Late"; date = tomorrow.

**Steps:** 1: Submit a sheet with status "Late" for S1. 2: Select tomorrow's date for a new session.

**Expected result:** Status "Late" is rejected with a validation error; the future date is rejected; nothing is saved.

**Actual result:** Fresh execution: 2 mapped test method(s) passed. Assertions cover the automated equivalent described by the named methods; this is not a claim of a separate literal manual execution.

**Result:** PASS automated equivalent

**Evidence:** `evidence/part3-2026-11-06/regression.json` (archived)

**Exact test methods:**

- `apps.attendance.test_marking.MarkingTests.test_invalid_status_is_rejected`
- `apps.attendance.test_marking.MarkingTests.test_future_day_rejected`

**Qualification:** Automated equivalent using isolated synthetic fixtures; literal manual example accounts and counts were not separately executed.

## UT_06_4  Verify safe handling of repeated submissions for the same session.

**Module:** Attendance Marking / BL-12, BL-13

**Preconditions:** Faculty is logged in and is assigned to the selected section and subject. Password and OTP verification are complete; any required first-login password change is complete.

**Parameters:**  Section A, CS101, 6 Oct, period 1 (twice).

**Steps:** Save a complete roster. Retry exactly the same assignment, date, period and statuses. Retry again with a changed status.

**Expected result:** The identical retry is acknowledged without duplicate records; a changed retry is rejected and the original marks remain unchanged.

**Actual result:** Fresh execution: 2 mapped test method(s) passed. Assertions cover the automated equivalent described by the named methods; this is not a claim of a separate literal manual execution.

**Result:** PASS automated equivalent

**Evidence:** `evidence/part3-2026-11-06/regression.json` (archived)

**Exact test methods:**

- `apps.attendance.test_submission_safety.SubmissionSafetyTests.test_same_post_can_be_retried_without_new_rows`
- `apps.attendance.test_submission_safety.SubmissionSafetyTests.test_changed_retry_cannot_overwrite_saved_values`

**Qualification:** Automated equivalent using isolated synthetic fixtures; literal manual example accounts and counts were not separately executed.

## UT_06_5  Verify the same subject can have two sessions on one date in different periods (AR-06).

**Module:** Attendance Marking / BL-12, BL-13

**Preconditions:** Faculty is logged in and is assigned to the selected section and subject. Password and OTP verification are complete; any required first-login password change is complete.

**Parameters:**  CS101, 6 Oct, periods 1 and 2.

**Steps:** 1: Submit CS101, 6 Oct, period 1. 2: Submit CS101, 6 Oct, period 2.

**Expected result:** Both sessions are saved; each student's CS101 held count increases by 2.

**Actual result:** Fresh execution: 1 mapped test method(s) passed. Assertions cover the automated equivalent described by the named methods; this is not a claim of a separate literal manual execution.

**Result:** PASS automated equivalent

**Evidence:** `evidence/part3-2026-11-06/regression.json` (archived)

**Exact test methods:**

- `apps.attendance.tests.AttendanceTests.test_same_subject_and_date_in_another_period_is_allowed`

**Qualification:** Automated equivalent using isolated synthetic fixtures; literal manual example accounts and counts were not separately executed.

## UT_06_6  Verify "Mark remaining as Present" fills only unmarked students (AR-07).

**Module:** Attendance Marking / BL-12, BL-13

**Preconditions:** Faculty is logged in and is assigned to the selected section and subject. Password and OTP verification are complete; any required first-login password change is complete.

**Parameters:** Two synthetic students ITS001 and ITS002. ITS001 is explicitly Present; ITS002 starts blank, then is explicitly marked Absent before the second fill action.

**Steps:** Open an unsubmitted two-student roster. Mark the first Present. Fill the remaining student as Present. Mark the second Absent, click Mark remaining as Present again, and save.

**Expected result:** Blank marks become Present; explicitly chosen Present and Absent marks remain unchanged, and the saved second record remains Absent.

**Actual result:** All eight final browser/viewport cases preserved explicitly selected Present and Absent marks and persisted the expected absence.

**Result:** PASS browser execution

**Evidence:** `evidence/part3-2026-11-06/browser-final/results.json` (archived)

**Qualification:** Automated equivalent using isolated synthetic fixtures; literal manual example accounts and counts were not separately executed.

## IT_06_1  Verify a saved session immediately updates students' attendance and the dashboards.

**Module:** Attendance Marking / BL-12, BL-13

**Preconditions:** Faculty is logged in and is assigned to the selected section and subject. Password and OTP verification are complete; any required first-login password change is complete.

**Parameters:**  Fixture data plus one session today.

**Steps:** 1: As F001, mark CS101 Section A for today, period 1: S001 Present, S002 Absent, S004 Present. 2: Log in as S002  >  My attendance. 3: Log in as ADMIN1  >  dashboard.

**Expected result:** S002's CS101 changes from 75/100 to 75/101 (74.26%) and S002 is shown below the threshold; the Admin dashboard shows 104 attendance sessions.

**Actual result:** Fresh execution: 2 mapped test method(s) passed. Assertions cover the automated equivalent described by the named methods; this is not a claim of a separate literal manual execution.

**Result:** PASS automated equivalent

**Evidence:** `evidence/part3-2026-11-06/regression.json` (archived)

**Exact test methods:**

- `apps.attendance.test_calculations.AttendanceCalculationTests.test_new_attendance_and_saved_corrections_recalculate_immediately`
- `apps.notifications.tests.StudentNotificationTests.test_st_10_1_equal_is_silent_then_one_drop_one_notification_and_email`

**Qualification:** Automated equivalent using isolated synthetic fixtures; literal manual example accounts and counts were not separately executed.

## IT_06_2  Verify Students cannot mark attendance and Faculty cannot mark another teacher's class (SEC-13).

**Module:** Attendance Marking / BL-12, BL-13

**Preconditions:** S001 and F002 are logged in (separate browsers). Password and OTP verification are complete; any required first-login password change is complete.

**Parameters:**  S001; F002; CS101 Section A.

**Steps:** 1: As S001, open /attendance/mark/. 2: As F002, request CS101 Section A (F001's class) through the address bar.

**Expected result:** Both requests show 'Access denied' (HTTP 403); no session is created; the denials are logged.

**Actual result:** Fresh execution: 2 mapped test method(s) passed. Assertions cover the automated equivalent described by the named methods; this is not a claim of a separate literal manual execution.

**Result:** PASS automated equivalent

**Evidence:** `evidence/part3-2026-11-06/regression.json` (archived)

**Exact test methods:**

- `apps.attendance.test_marking.MarkingTests.test_student_cannot_mark_attendance`
- `apps.attendance.test_marking.MarkingTests.test_unassigned_class_is_forbidden`

**Qualification:** Automated equivalent using isolated synthetic fixtures; literal manual example accounts and counts were not separately executed.

## IT_06_3  Verify a saved session persists after logout and login.

**Module:** Attendance Marking / BL-12, BL-13

**Preconditions:** Faculty is logged in and is assigned to the selected section and subject. Password and OTP verification are complete; any required first-login password change is complete.

**Parameters:**  Today, period 2.

**Steps:** 1: As F001, save CS101 Section A for today, period 2. 2: Log out and log in. 3: Load the same class, date and period.

**Expected result:** The page shows 'This attendance session is already saved' with the same statuses; no duplicate session exists.

**Actual result:** Fresh execution: 1 mapped test method(s) passed. Assertions cover the automated equivalent described by the named methods; this is not a claim of a separate literal manual execution.

**Result:** PASS automated equivalent

**Evidence:** `evidence/part3-2026-11-06/regression.json` (archived)

**Exact test methods:**

- `apps.attendance.test_marking.MarkingTests.test_saves_all_records_and_survives_relogin`

**Qualification:** Automated equivalent using isolated synthetic fixtures; literal manual example accounts and counts were not separately executed.

## ST_06_1  End-to-end system test: complete the full "Mark Attendance" workflow as an actual user would.

**Module:** Attendance Marking / BL-12, BL-13

**Preconditions:** Faculty is logged in and is assigned to the selected section and subject. Password and OTP verification are complete; any required first-login password change is complete.

**Parameters:**  F001; CS101 Section A; today; period 3; S001 Present, S002 Present, S004 Absent.

**Steps:** 1: Faculty selects the class/section, subject, date, and period. 2: System displays the enrolled, active student list. 3: Faculty marks each student Present or Absent. 4: Faculty submits the attendance. 5: System saves the session, recalculates percentages, and runs the threshold check.

**Expected result:** The session is saved; each student's subject and overall counts increase by one session; the threshold check runs (UC-10).

**Actual result:** Fresh execution: 1 mapped test method(s) passed. Assertions cover the automated equivalent described by the named methods; this is not a claim of a separate literal manual execution.

**Result:** PASS automated equivalent

**Evidence:** `evidence/part3-2026-11-06/regression.json` (archived)

**Exact test methods:**

- `apps.attendance.test_marking.MarkingTests.test_saves_all_records_and_survives_relogin`

**Qualification:** Automated equivalent using isolated synthetic fixtures; literal manual example accounts and counts were not separately executed.

## ST_06_2  System test: verify the exception flow  -  Faculty tries to mark attendance for a class not assigned to them: system denies access.

**Module:** Attendance Marking / BL-12, BL-13

**Preconditions:** Faculty is logged in and is assigned to the selected section and subject. Password and OTP verification are complete; any required first-login password change is complete.

**Parameters:**  F002; CS101 Section A.

**Steps:** 1: As F002, open Mark attendance. 2: Request CS101 Section A (F001's class) through the address bar.

**Expected result:** 'Access denied' (HTTP 403); nothing is saved; the attempt is logged.

**Actual result:** Fresh execution: 2 mapped test method(s) passed. Assertions cover the automated equivalent described by the named methods; this is not a claim of a separate literal manual execution.

**Result:** PASS automated equivalent

**Evidence:** `evidence/part3-2026-11-06/regression.json` (archived)

**Exact test methods:**

- `apps.attendance.test_marking.MarkingTests.test_student_cannot_mark_attendance`
- `apps.attendance.test_marking.MarkingTests.test_unassigned_class_is_forbidden`

**Qualification:** Automated equivalent using isolated synthetic fixtures; literal manual example accounts and counts were not separately executed.

## ST_06_3  Verify a missed past session can be created inside the correction window (AR-06, AR-08).

**Module:** Attendance Marking / BL-12, BL-13

**Preconditions:** Faculty is logged in and is assigned to the selected section and subject. Password and OTP verification are complete; any required first-login password change is complete.

**Parameters:**  Today 8 Oct; session date 6 Oct.

**Steps:** 1: On 8 Oct, select CS101 with session date 6 Oct, period 1. 2: Mark all students and submit.

**Expected result:** The session is saved (the window is open until 8 Oct 23:59:59).

**Actual result:** Fresh execution: 1 mapped test method(s) passed. Assertions cover the automated equivalent described by the named methods; this is not a claim of a separate literal manual execution.

**Result:** PASS automated equivalent

**Evidence:** `evidence/part3-2026-11-06/regression.json` (archived)

**Exact test methods:**

- `apps.attendance.test_marking_window.FacultyDateWindowTests.test_faculty_can_record_on_the_last_day_of_the_window`

**Qualification:** Automated equivalent using isolated synthetic fixtures; literal manual example accounts and counts were not separately executed.

## ST_06_4  Verify a past session outside the correction window cannot be created by faculty (UC-06 1c).

**Module:** Attendance Marking / BL-12, BL-13

**Preconditions:** Faculty is logged in and is assigned to the selected section and subject. Password and OTP verification are complete; any required first-login password change is complete.

**Parameters:**  Today 9 Oct; session date 6 Oct.

**Steps:** 1: On 9 Oct, select CS101 with session date 6 Oct, period 1.

**Expected result:** The faculty member is blocked with a message to contact the Admin; nothing is saved.

**Actual result:** Fresh execution: 1 mapped test method(s) passed. Assertions cover the automated equivalent described by the named methods; this is not a claim of a separate literal manual execution.

**Result:** PASS automated equivalent

**Evidence:** `evidence/part3-2026-11-06/regression.json` (archived)

**Exact test methods:**

- `apps.attendance.test_marking_window.FacultyDateWindowTests.test_faculty_cannot_record_the_day_after_the_window`

**Qualification:** Automated equivalent using isolated synthetic fixtures; literal manual example accounts and counts were not separately executed.

## UT_07_1  Verify Update/Correct Attendance succeeds with valid input.

**Module:** Attendance Correction / BL-17, BL-18

**Preconditions:** An attendance record for the class/date already exists.

**Parameters:**  Session on 6 Oct, S2 Absent; edit made on 7 Oct.

**Steps:** 1: Faculty opens a previously submitted attendance record. 2: Faculty changes S2 from Absent to Present. 3: System validates the faculty assignment and the correction window.

**Expected result:** S2 changes to Present; the audit entry shows faculty, time, old value Absent, and new value Present; percentages are updated.

**Actual result:** Fresh execution: 1 mapped test method(s) passed. Assertions cover the automated equivalent described by the named methods; this is not a claim of a separate literal manual execution.

**Result:** PASS automated equivalent

**Evidence:** `evidence/part3-2026-11-06/regression.json` (archived)

**Exact test methods:**

- `apps.attendance.test_corrections.AttendanceCorrectionTests.test_faculty_correction_persists_with_exact_audit_and_recorder_unchanged`

**Qualification:** Automated equivalent using isolated synthetic fixtures; literal manual example accounts and counts were not separately executed.

## UT_07_2  Verify a correction without a change, or an Admin correction without a reason, is rejected.

**Module:** Attendance Correction / BL-17, BL-18

**Preconditions:** An attendance record for the class/date already exists.

**Parameters:**  Session from today; blank reason.

**Steps:** 1: As F001, open today's CS101 session for correction and save without changing any status. 2: As ADMIN1, change a status and leave the reason blank.

**Expected result:** Step 1 reports that nothing changed; step 2 is rejected with 'Reason is required.'; no record or log entry changes.

**Actual result:** Fresh execution: 2 mapped test method(s) passed. Assertions cover the automated equivalent described by the named methods; this is not a claim of a separate literal manual execution.

**Result:** PASS automated equivalent

**Evidence:** `evidence/part3-2026-11-06/regression.json` (archived)

**Exact test methods:**

- `apps.attendance.test_corrections.AttendanceCorrectionTests.test_invalid_statuses_no_op_and_future_records_are_rejected_without_audit`
- `apps.attendance.test_corrections.AttendanceCorrectionTests.test_admin_override_after_deadline_requires_reason_and_is_logged`

**Qualification:** Automated equivalent using isolated synthetic fixtures; literal manual example accounts and counts were not separately executed.

## UT_07_3  Verify a correction with a status other than Present or Absent is rejected.

**Module:** Attendance Correction / BL-17, BL-18

**Preconditions:** An attendance record for the class/date already exists.

**Parameters:**  Status 'L' (Late).

**Steps:** 1: Open a saved session for correction. 2: Submit S001's status as 'L'. 3: Save.

**Expected result:** Rejected: only Present or Absent are allowed; the record is unchanged.

**Actual result:** Fresh execution: 2 mapped test method(s) passed. Assertions cover the automated equivalent described by the named methods; this is not a claim of a separate literal manual execution.

**Result:** PASS automated equivalent

**Evidence:** `evidence/part3-2026-11-06/regression.json` (archived)

**Exact test methods:**

- `apps.attendance.test_corrections.AttendanceCorrectionTests.test_invalid_statuses_no_op_and_future_records_are_rejected_without_audit`
- `apps.attendance.test_corrections.AttendanceCorrectionTests.test_admin_override_after_deadline_requires_reason_and_is_logged`

**Qualification:** Automated equivalent using isolated synthetic fixtures; literal manual example accounts and counts were not separately executed.

## UT_07_4  Verify a faculty correction at the last minute of the window is accepted (AR-08).

**Module:** Attendance Correction / BL-17, BL-18

**Preconditions:** An attendance record for the class/date already exists.

**Parameters:**  Session 6 Oct; edit 8 Oct 23:59 IST.

**Steps:** 1: On 8 Oct at 23:59, change S2 from Absent to Present for the 6 Oct session.

**Expected result:** The correction is saved and logged with old and new values.

**Actual result:** Fresh execution: 1 mapped test method(s) passed. Assertions cover the automated equivalent described by the named methods; this is not a claim of a separate literal manual execution.

**Result:** PASS automated equivalent

**Evidence:** `evidence/part3-2026-11-06/regression.json` (archived)

**Exact test methods:**

- `apps.attendance.test_corrections.AttendanceCorrectionTests.test_last_microsecond_of_second_day_ist_is_allowed`

**Qualification:** Automated equivalent using isolated synthetic fixtures; literal manual example accounts and counts were not separately executed.

## UT_07_5  Verify the Admin can set the correction window only to 0-30 days (AR-08).

**Module:** Attendance Correction / BL-17, BL-18

**Preconditions:** Admin is logged in. Password and OTP verification are complete; any required first-login password change is complete.

**Parameters:**  -1, 31, 2.5, and 3.

**Steps:** 1: Open the correction window setting. 2: Enter each test value and save.

**Expected result:** -1, 31, and 2.5 are rejected with a validation message; 3 is accepted and logged.

**Actual result:** Fresh execution: 1 mapped test method(s) passed. Assertions cover the automated equivalent described by the named methods; this is not a claim of a separate literal manual execution.

**Result:** PASS automated equivalent

**Evidence:** `evidence/part3-2026-11-06/regression.json` (archived)

**Exact test methods:**

- `apps.attendance.test_corrections.CorrectionWindowTests.test_setting_requires_active_admin_reason_valid_integer_and_a_change`

**Qualification:** Automated equivalent using isolated synthetic fixtures; literal manual example accounts and counts were not separately executed.

## IT_07_1  Verify a correction updates the student's percentage and the dashboards.

**Module:** Attendance Correction / BL-17, BL-18

**Preconditions:** An attendance record for the class/date already exists.

**Parameters:**  S002: Absent  >  Present.

**Steps:** 1: As F001, correct S002 from Absent to Present in today's CS101 session (from IT_06_1). 2: Log in as S002  >  My attendance.

**Expected result:** S002's CS101 changes from 75/101 (74.26%) to 76/101 (75.25%) and S002 is no longer shown below the threshold.

**Actual result:** Fresh execution: 1 mapped test method(s) passed. Assertions cover the automated equivalent described by the named methods; this is not a claim of a separate literal manual execution.

**Result:** PASS automated equivalent

**Evidence:** `evidence/part3-2026-11-06/regression.json` (archived)

**Exact test methods:**

- `apps.attendance.test_corrections.AttendanceCorrectionTests.test_saved_correction_updates_calculations_and_all_dashboards`

**Qualification:** Automated equivalent using isolated synthetic fixtures; literal manual example accounts and counts were not separately executed.

## IT_07_2  Verify only the assigned faculty member (or the Admin) can correct a record.

**Module:** Attendance Correction / BL-17, BL-18

**Preconditions:** Faculty F2 (not assigned to Section A) and Student S1 accounts exist.

**Parameters:**  F2 and S1 credentials; Section A session on 6 Oct.

**Steps:** 1: Log in as F2 and try to edit a Section A record. 2: Repeat as S1.

**Expected result:** Both attempts are denied; the record is unchanged; the denials are logged.

**Actual result:** Fresh execution: 1 mapped test method(s) passed. Assertions cover the automated equivalent described by the named methods; this is not a claim of a separate literal manual execution.

**Result:** PASS automated equivalent

**Evidence:** `evidence/part3-2026-11-06/regression.json` (archived)

**Exact test methods:**

- `apps.attendance.test_corrections.AttendanceCorrectionTests.test_student_other_faculty_and_inactive_cached_actor_are_denied`

**Qualification:** Automated equivalent using isolated synthetic fixtures; literal manual example accounts and counts were not separately executed.

## IT_07_3  Verify a correction and its history persist after logout and login.

**Module:** Attendance Correction / BL-17, BL-18

**Preconditions:** An attendance record for the class/date already exists.

**Parameters:**  S004: Present  >  Absent.

**Steps:** 1: As F001, correct S004 from Present to Absent in today's session. 2: Log out and log in as ADMIN1. 3: Open the modification history.

**Expected result:** The record shows Absent; the history shows F001, the time, old value Present and new value Absent.

**Actual result:** Fresh execution: 1 mapped test method(s) passed. Assertions cover the automated equivalent described by the named methods; this is not a claim of a separate literal manual execution.

**Result:** PASS automated equivalent

**Evidence:** `evidence/part3-2026-11-06/regression.json` (archived)

**Exact test methods:**

- `apps.attendance.test_corrections.AttendanceCorrectionTests.test_faculty_correction_persists_with_exact_audit_and_recorder_unchanged`

**Qualification:** Automated equivalent using isolated synthetic fixtures; literal manual example accounts and counts were not separately executed.

## ST_07_1  End-to-end system test: complete the full "Update/Correct Attendance" workflow as an actual user would.

**Module:** Attendance Correction / BL-17, BL-18

**Preconditions:** An attendance record for the class/date already exists.

**Parameters:**  F001; today's CS101 Section A session; S004 Present  >  Absent.

**Steps:** 1: Faculty opens a previously submitted attendance record. 2: Faculty changes a student's status. 3: System validates the faculty assignment and the correction window. 4: System saves the correction, logs it with old and new values, and recalculates percentages.

**Expected result:** The correction is saved, logged with old and new values, and S004's percentage updates immediately.

**Actual result:** Fresh execution: 1 mapped test method(s) passed. Assertions cover the automated equivalent described by the named methods; this is not a claim of a separate literal manual execution.

**Result:** PASS automated equivalent

**Evidence:** `evidence/part3-2026-11-06/regression.json` (archived)

**Exact test methods:**

- `apps.attendance.test_corrections.AttendanceCorrectionTests.test_faculty_correction_persists_with_exact_audit_and_recorder_unchanged`

**Qualification:** Automated equivalent using isolated synthetic fixtures; literal manual example accounts and counts were not separately executed.

## ST_07_2  System test: verify the exception flow  -  Faculty attempts to edit a record outside the permitted correction window: system blocks the edit.

**Module:** Attendance Correction / BL-17, BL-18

**Preconditions:** An attendance record for the class/date already exists.

**Parameters:**  Session on 6 Oct; edit attempted on 9 Oct at 00:00 (window closed at 8 Oct 23:59:59 IST).

**Steps:** 1: Log in as the assigned faculty member on 9 Oct at 00:00. 2: Try to change S2 from Absent to Present for the 6 Oct session.

**Expected result:** The edit is blocked with "Correction window closed - contact the Admin"; the record is unchanged.

**Actual result:** Fresh execution: 1 mapped test method(s) passed. Assertions cover the automated equivalent described by the named methods; this is not a claim of a separate literal manual execution.

**Result:** PASS automated equivalent

**Evidence:** `evidence/part3-2026-11-06/regression.json` (archived)

**Exact test methods:**

- `apps.attendance.test_corrections.AttendanceCorrectionTests.test_first_instant_of_third_day_ist_is_blocked`

**Qualification:** Automated equivalent using isolated synthetic fixtures; literal manual example accounts and counts were not separately executed.

## ST_07_3  Verify the Admin can correct a record after the window with a reason (UC-07 3c).

**Module:** Attendance Correction / BL-17, BL-18

**Preconditions:** Admin is logged in; window for the 6 Oct session has closed. Password and OTP verification are complete; any required first-login password change is complete.

**Parameters:**  Reason "Student submitted medical certificate".

**Steps:** 1: On 12 Oct, change S2 from Absent to Present for the 6 Oct session. 2: Enter a reason and save. 3: Open the modification history.

**Expected result:** The change is saved; the history shows Admin, time, old value Absent, new value Present, the reason, and an "Admin override" flag; percentages are updated.

**Actual result:** Fresh execution: 1 mapped test method(s) passed. Assertions cover the automated equivalent described by the named methods; this is not a claim of a separate literal manual execution.

**Result:** PASS automated equivalent

**Evidence:** `evidence/part3-2026-11-06/regression.json` (archived)

**Exact test methods:**

- `apps.attendance.test_corrections.AttendanceCorrectionTests.test_admin_override_after_deadline_requires_reason_and_is_logged`

**Qualification:** Automated equivalent using isolated synthetic fixtures; literal manual example accounts and counts were not separately executed.

## ST_07_4  Verify an Admin correction without a reason is rejected (UC-07 3c).

**Module:** Attendance Correction / BL-17, BL-18

**Preconditions:** Admin is logged in. Password and OTP verification are complete; any required first-login password change is complete.

**Parameters:**  Blank reason.

**Steps:** 1: Change S2's status for the 6 Oct session. 2: Leave the reason blank and save.

**Expected result:** The change is rejected with "Reason is required"; the record is unchanged.

**Actual result:** Fresh execution: 1 mapped test method(s) passed. Assertions cover the automated equivalent described by the named methods; this is not a claim of a separate literal manual execution.

**Result:** PASS automated equivalent

**Evidence:** `evidence/part3-2026-11-06/regression.json` (archived)

**Exact test methods:**

- `apps.attendance.test_corrections.AttendanceCorrectionTests.test_admin_override_after_deadline_requires_reason_and_is_logged`

**Qualification:** Automated equivalent using isolated synthetic fixtures; literal manual example accounts and counts were not separately executed.

## ST_07_5  Verify the Admin can record a missed session after the window with a reason (AR-08).

**Module:** Attendance Correction / BL-17, BL-18

**Preconditions:** Admin is logged in; no CS101 session exists for 6 Oct, period 3. Password and OTP verification are complete; any required first-login password change is complete.

**Parameters:**  Reason "Session was not recorded".

**Steps:** 1: On 12 Oct, create the 6 Oct, period 3 session for CS101. 2: Mark all students, enter a reason, and save.

**Expected result:** The session is saved and logged as an Admin override with the reason.

**Actual result:** Fresh execution: 1 mapped test method(s) passed. Assertions cover the automated equivalent described by the named methods; this is not a claim of a separate literal manual execution.

**Result:** PASS automated equivalent

**Evidence:** `evidence/part3-2026-11-06/regression.json` (archived)

**Exact test methods:**

- `apps.attendance.test_marking_window.FacultyDateWindowTests.test_admin_can_record_an_old_missed_session_with_a_reason`

**Qualification:** Automated equivalent using isolated synthetic fixtures; literal manual example accounts and counts were not separately executed.

## UT_08_1  Verify View Attendance succeeds with valid input.

**Module:** Attendance Viewing / BL-14, BL-15, BL-16

**Preconditions:** User is logged in. Password and OTP verification are complete; any required first-login password change is complete.

**Parameters:**  S001 logged in; no filters.

**Steps:** 1: User navigates to the Attendance view. 2: User selects a subject or date range (optional). 3: System retrieves and displays the relevant attendance records.

**Expected result:** My attendance shows CS101 74/100 (74.00%), MA101 2/3 (66.67%) and overall 76/103 (73.79%).

**Actual result:** Fresh execution: 1 mapped test method(s) passed. Assertions cover the automated equivalent described by the named methods; this is not a claim of a separate literal manual execution.

**Result:** PASS automated equivalent

**Evidence:** `evidence/part3-2026-11-06/regression.json` (archived)

**Exact test methods:**

- `apps.attendance.test_calculations.AttendanceCalculationTests.test_known_subject_and_pooled_overall_results`

**Qualification:** Automated equivalent using isolated synthetic fixtures; literal manual example accounts and counts were not separately executed.

## UT_08_2  Verify subject filter returns only the selected subject.

**Module:** Attendance Viewing / BL-15

**Preconditions:** Student S001 is logged in; S001 has records in CS101 and MA101. Password and OTP verification are complete; any required first-login password change is complete.

**Parameters:**  S001: CS101 74/100; MA101 2/3.

**Steps:** 1: Open My attendance. 2: Select CS101. 3: Apply the filter.

**Expected result:** Only CS101 appears: 74/100 (74.00%); the overall total for the filter is 74/100 (74.00%).

**Actual result:** Fresh execution: 1 mapped test method(s) passed. Assertions cover the automated equivalent described by the named methods; this is not a claim of a separate literal manual execution.

**Result:** PASS automated equivalent

**Evidence:** `evidence/part3-2026-11-06/regression.json` (archived)

**Exact test methods:**

- `apps.attendance.test_backlog_suhas.BacklogFeatureTests.test_student_report_filters_by_subject_and_inclusive_date_range`

**Qualification:** Automated equivalent using isolated synthetic fixtures; literal manual example accounts and counts were not separately executed.

## UT_08_3  Verify inclusive date filters and invalid date-range handling.

**Module:** Attendance Viewing / BL-15

**Preconditions:** Student S001 is logged in and has MA101 attendance on 1, 2 and 3 Oct 2026. Password and OTP verification are complete; any required first-login password change is complete.

**Parameters:**  1 Oct Present; 2 Oct Absent; 3 Oct Present; range 2-3 Oct 2026.

**Steps:** 1: Filter from 2 Oct through 3 Oct. 2: Verify matching totals. 3: Reverse the date range and submit.

**Expected result:** The 2-3 Oct range includes both boundary dates: MA101 1/2 (50.00%), excluding 1 Oct. A reversed range shows 'End date must be on or after the start date.' and no totals.

**Actual result:** Fresh execution: 2 mapped test method(s) passed. Assertions cover the automated equivalent described by the named methods; this is not a claim of a separate literal manual execution.

**Result:** PASS automated equivalent

**Evidence:** `evidence/part3-2026-11-06/regression.json` (archived)

**Exact test methods:**

- `apps.attendance.test_backlog_suhas.BacklogFeatureTests.test_student_report_filters_by_subject_and_inclusive_date_range`
- `apps.attendance.test_backlog_suhas.BacklogFeatureTests.test_student_report_rejects_reversed_date_range`

**Qualification:** Automated equivalent using isolated synthetic fixtures; literal manual example accounts and counts were not separately executed.

## UT_08_4  Verify the subject percentage formula and display (AR-09, AR-11).

**Module:** Attendance Viewing / BL-14, BL-15, BL-16

**Preconditions:** User is logged in. Password and OTP verification are complete; any required first-login password change is complete.

**Parameters:**  S1 Subject A: 2 of 3 Present.

**Steps:** 1: Calculate and display Subject A for S1.

**Expected result:** Displays 2/3 (66.67%).

**Actual result:** Fresh execution: 1 mapped test method(s) passed. Assertions cover the automated equivalent described by the named methods; this is not a claim of a separate literal manual execution.

**Result:** PASS automated equivalent

**Evidence:** `evidence/part3-2026-11-06/regression.json` (archived)

**Exact test methods:**

- `apps.attendance.test_calculations.AttendanceCalculationTests.test_known_subject_and_pooled_overall_results`

**Qualification:** Automated equivalent using isolated synthetic fixtures; literal manual example accounts and counts were not separately executed.

## UT_08_5  Verify rounding is half up to 2 decimals (AR-11).

**Module:** Attendance Viewing / BL-14, BL-15, BL-16

**Preconditions:** User is logged in. Password and OTP verification are complete; any required first-login password change is complete.

**Parameters:**  1 of 160 sessions attended (exact value 0.625%).

**Steps:** 1: Calculate and display the percentage.

**Expected result:** Displays 1/160 (0.63%), not 0.62%.

**Actual result:** Fresh execution: 1 mapped test method(s) passed. Assertions cover the automated equivalent described by the named methods; this is not a claim of a separate literal manual execution.

**Result:** PASS automated equivalent

**Evidence:** `evidence/part3-2026-11-06/regression.json` (archived)

**Exact test methods:**

- `apps.attendance.test_calculations.AttendanceCalculationTests.test_rounding_is_half_up_with_two_decimal_places`

**Qualification:** Automated equivalent using isolated synthetic fixtures; literal manual example accounts and counts were not separately executed.

## UT_08_6  Verify the overall percentage is pooled, not averaged (AR-10).

**Module:** Attendance Viewing / BL-14, BL-15, BL-16

**Preconditions:** User is logged in. Password and OTP verification are complete; any required first-login password change is complete.

**Parameters:**  Subject A 10/12; Subject B 8/10.

**Steps:** 1: Calculate the overall figure for S1.

**Expected result:** Displays 18/22 (81.82%), not 81.67%.

**Actual result:** Fresh execution: 1 mapped test method(s) passed. Assertions cover the automated equivalent described by the named methods; this is not a claim of a separate literal manual execution.

**Result:** PASS automated equivalent

**Evidence:** `evidence/part3-2026-11-06/regression.json` (archived)

**Exact test methods:**

- `apps.attendance.test_calculations.AttendanceCalculationTests.test_known_subject_and_pooled_overall_results`

**Qualification:** Automated equivalent using isolated synthetic fixtures; literal manual example accounts and counts were not separately executed.

## UT_08_7  Verify zero sessions shows N/A (AR-11).

**Module:** Attendance Viewing / BL-14, BL-15, BL-16

**Preconditions:** User is logged in. Password and OTP verification are complete; any required first-login password change is complete.

**Parameters:**  Subject C: 0 sessions.

**Steps:** 1: View a subject with no sessions held.

**Expected result:** Displays "N/A - no classes yet"; no error; no 0% or 100% is shown.

**Actual result:** Fresh execution: 1 mapped test method(s) passed. Assertions cover the automated equivalent described by the named methods; this is not a claim of a separate literal manual execution.

**Result:** PASS automated equivalent

**Evidence:** `evidence/part3-2026-11-06/regression.json` (archived)

**Exact test methods:**

- `apps.attendance.test_calculations.AttendanceCalculationTests.test_enrolled_subjects_without_classes_and_overall_are_na`

**Qualification:** Automated equivalent using isolated synthetic fixtures; literal manual example accounts and counts were not separately executed.

## IT_08_1  Verify the student's report and dashboard show the same figures.

**Module:** Attendance Viewing / BL-14, BL-15, BL-16

**Preconditions:** User is logged in. Password and OTP verification are complete; any required first-login password change is complete.

**Parameters:**  S001 fixture data; threshold 75%.

**Steps:** 1: As S001, open My attendance. 2: Open the Student dashboard.

**Expected result:** Both show overall 76/103 (73.79%); the dashboard says overall attendance is below the threshold and 2 subjects are below it.

**Actual result:** Fresh execution: 2 mapped test method(s) passed. Assertions cover the automated equivalent described by the named methods; this is not a claim of a separate literal manual execution.

**Result:** PASS automated equivalent

**Evidence:** `evidence/part3-2026-11-06/regression.json` (archived)

**Exact test methods:**

- `apps.attendance.test_summary.StudentAttendanceSummaryTests.test_subject_and_overall_counts_are_displayed`
- `apps.attendance.test_backlog_suhas.BacklogFeatureTests.test_dashboard_statistics_are_role_scoped_and_present`

**Qualification:** Automated equivalent using isolated synthetic fixtures; literal manual example accounts and counts were not separately executed.

## IT_08_2  Verify a student cannot view another student's attendance (SEC-12).

**Module:** Attendance Viewing / BL-14, BL-15, BL-16

**Preconditions:** Students S1 and S2 exist.

**Parameters:**  S1 credentials; S2's student ID.

**Steps:** 1: Log in as S1. 2: Request S2's attendance by changing the ID in the address.

**Expected result:** Access is denied; no S2 data is shown; the attempt is logged.

**Actual result:** Fresh execution: 1 mapped test method(s) passed. Assertions cover the automated equivalent described by the named methods; this is not a claim of a separate literal manual execution.

**Result:** PASS automated equivalent

**Evidence:** `evidence/part3-2026-11-06/regression.json` (archived)

**Exact test methods:**

- `apps.accounts.test_permissions.ScopeTests.test_student_cannot_fetch_another_students_record_by_id`

**Qualification:** Automated equivalent using isolated synthetic fixtures; literal manual example accounts and counts were not separately executed.

## IT_08_3  Verify a student's attendance figures are unchanged after logout and login.

**Module:** Attendance Viewing / BL-14, BL-15, BL-16

**Preconditions:** User is logged in. Password and OTP verification are complete; any required first-login password change is complete.

**Parameters:**  S004.

**Steps:** 1: As S004, open My attendance. 2: Log out and log back in. 3: Open My attendance again.

**Expected result:** Both times: CS101 76/100 (76.00%) and overall 76/100 (76.00%).

**Actual result:** Fresh execution: 1 mapped test method(s) passed. Assertions cover the automated equivalent described by the named methods; this is not a claim of a separate literal manual execution.

**Result:** PASS automated equivalent

**Evidence:** `evidence/part3-2026-11-06/regression.json` (archived)

**Exact test methods:**

- `apps.attendance.tests.AttendanceTests.test_record_relationships_survive_reload`

**Qualification:** Automated equivalent using isolated synthetic fixtures; literal manual example accounts and counts were not separately executed.

## IT_08_4  Verify faculty cannot view attendance of a student outside their assigned classes (AR-02).

**Module:** Attendance Viewing / BL-14, BL-15, BL-16

**Preconditions:** F1 is assigned to Section A only; S4 is in Section B.

**Parameters:**  F1 credentials; S4.

**Steps:** 1: Log in as F1. 2: Request S4's attendance.

**Expected result:** Access is denied; no S4 data is shown; the attempt is logged.

**Actual result:** Fresh execution: 1 mapped test method(s) passed. Assertions cover the automated equivalent described by the named methods; this is not a claim of a separate literal manual execution.

**Result:** PASS automated equivalent

**Evidence:** `evidence/part3-2026-11-06/regression.json` (archived)

**Exact test methods:**

- `apps.attendance.test_calculations.AttendanceCalculationTests.test_scope_filters_both_history_and_zero_class_enrollments`

**Qualification:** Automated equivalent using isolated synthetic fixtures; literal manual example accounts and counts were not separately executed.

## ST_08_1  End-to-end system test: complete the full "View Attendance" workflow as an actual user would.

**Module:** Attendance Viewing / BL-14, BL-15, BL-16

**Preconditions:** User is logged in. Password and OTP verification are complete; any required first-login password change is complete.

**Parameters:**  S1: Subject A 10 of 12 Present; Subject B 8 of 10 Present.

**Steps:** 1: User navigates to the Attendance view. 2: User selects a subject or date range (optional). 3: System retrieves and displays the relevant attendance records. 4: System displays, for each subject, attended/held and the percentage, plus the overall total.

**Expected result:** Subject A shows 10/12 (83.33%); Subject B shows 8/10 (80.00%); Overall shows 18/22 (81.82%).

**Actual result:** Fresh execution: 1 mapped test method(s) passed. Assertions cover the automated equivalent described by the named methods; this is not a claim of a separate literal manual execution.

**Result:** PASS automated equivalent

**Evidence:** `evidence/part3-2026-11-06/regression.json` (archived)

**Exact test methods:**

- `apps.attendance.test_calculations.AttendanceCalculationTests.test_known_subject_and_pooled_overall_results`

**Qualification:** Automated equivalent using isolated synthetic fixtures; literal manual example accounts and counts were not separately executed.

## ST_08_2  System test: verify the exception flow  -  No attendance records exist yet for the selected filter: system shows an empty state message.

**Module:** Attendance Viewing / BL-14, BL-15, BL-16

**Preconditions:** User is logged in. Password and OTP verification are complete; any required first-login password change is complete.

**Parameters:**  S003 (enrolled in MA101, no recorded classes).

**Steps:** 1: As S003, open My attendance without filters.

**Expected result:** MA101 and overall both show 'N/A - no classes yet'; no 0% is shown and S003 is not flagged.

**Actual result:** Fresh execution: 1 mapped test method(s) passed. Assertions cover the automated equivalent described by the named methods; this is not a claim of a separate literal manual execution.

**Result:** PASS automated equivalent

**Evidence:** `evidence/part3-2026-11-06/regression.json` (archived)

**Exact test methods:**

- `apps.attendance.test_calculations.AttendanceCalculationTests.test_enrolled_subjects_without_classes_and_overall_are_na`

**Qualification:** Automated equivalent using isolated synthetic fixtures; literal manual example accounts and counts were not separately executed.

## IT_08_5  Verify query parameters cannot expose another student's report.

**Module:** Attendance Viewing / BL-15 / SEC-12

**Preconditions:** Students S001 and S002 exist; S001 is logged in. Password and OTP verification are complete; any required first-login password change is complete.

**Parameters:**  URL contains S002's student ID; S001 is logged in.

**Steps:** 1: Request /attendance/mine/?student=<S002 id>. 2: Inspect identity and attendance shown.

**Expected result:** Only S001's own report is shown (overall 76/103 (73.79%)); S002's identity and totals are not disclosed.

**Actual result:** Fresh execution: 1 mapped test method(s) passed. Assertions cover the automated equivalent described by the named methods; this is not a claim of a separate literal manual execution.

**Result:** PASS automated equivalent

**Evidence:** `evidence/part3-2026-11-06/regression.json` (archived)

**Exact test methods:**

- `apps.attendance.test_summary.StudentAttendanceSummaryTests.test_query_parameters_cannot_select_another_student`

**Qualification:** Automated equivalent using isolated synthetic fixtures; literal manual example accounts and counts were not separately executed.

## ST_08_3  Verify no matching attendance has a clear empty state.

**Module:** Attendance Viewing / BL-15

**Preconditions:** Student S001 is logged in with saved attendance outside the chosen date range. Password and OTP verification are complete; any required first-login password change is complete.

**Parameters:**  From 10 Oct 2026 through 11 Oct 2026; no records in this period.

**Steps:** 1: Select a date range with no saved records. 2: Apply filters.

**Expected result:** Subject table displays 'No attendance records match these filters.' and overall displays N/A  -  no classes yet.

**Actual result:** Fresh execution: 1 mapped test method(s) passed. Assertions cover the automated equivalent described by the named methods; this is not a claim of a separate literal manual execution.

**Result:** PASS automated equivalent

**Evidence:** `evidence/part3-2026-11-06/regression.json` (archived)

**Exact test methods:**

- `apps.attendance.test_backlog_suhas.BacklogFeatureTests.test_student_report_shows_empty_state_for_date_with_no_records`

**Qualification:** Automated equivalent using isolated synthetic fixtures; literal manual example accounts and counts were not separately executed.

## UT_09_1  Verify Generate & Export Reports succeeds with valid input.

**Module:** Reporting / BL-20, BL-21

**Preconditions:** User is logged in with reporting privileges. Password and OTP verification are complete; any required first-login password change is complete. Select an explicit authorized report scope and both inclusive date bounds.

**Parameters:**  ADMIN1; scope Section A, subject CS101; 1 to 30 June 2026.

**Steps:** 1: User navigates to the Reports screen. 2: User selects report scope (student/class/subject) and date range. 3: System compiles the report.

**Expected result:** The report lists S001 74/100 (74.00%), S002 75/100 (75.00%) and S004 76/100 (76.00%) for CS101 in Section A.

**Actual result:** Fresh execution: 2 mapped test method(s) passed. Assertions cover the automated equivalent described by the named methods; this is not a claim of a separate literal manual execution.

**Result:** PASS automated equivalent

**Evidence:** `evidence/part3-2026-11-06/regression.json` (archived)

**Exact test methods:**

- `tests.test_integration.ProvisionedAttendanceJourneyTests.test_provisioned_accounts_complete_otp_then_corrected_totals_agree_everywhere`
- `tests.test_integration.AttendanceAlertAndReportIntegrationTests.test_exports_are_private_audited_and_invalid_or_empty_exports_are_not_downloads`

**Qualification:** Automated equivalent using isolated synthetic fixtures; literal manual example accounts and counts were not separately executed.

## UT_09_2  Verify a report request without a scope or date range is rejected.

**Module:** Reporting / BL-20, BL-21

**Preconditions:** User is logged in with reporting privileges. Password and OTP verification are complete; any required first-login password change is complete.

**Parameters:**  Blank scope and dates.

**Steps:** 1: Open Reports. 2: Leave scope and dates empty. 3: Generate.

**Expected result:** A required-field message for scope and dates; no report or file is produced.

**Actual result:** Fresh execution: 1 mapped test method(s) passed. Assertions cover the automated equivalent described by the named methods; this is not a claim of a separate literal manual execution.

**Result:** PASS automated equivalent

**Evidence:** `evidence/part3-2026-11-06/regression.json` (archived)

**Exact test methods:**

- `tests.test_report_scope.ReportScopeTests.test_blank_partial_or_missing_scope_cannot_generate_or_export`

**Qualification:** Automated equivalent using isolated synthetic fixtures; literal manual example accounts and counts were not separately executed.

## UT_09_3  Verify a reversed date range and an unsupported export format are rejected (UC-09 4a).

**Module:** Reporting / BL-20, BL-21

**Preconditions:** User is logged in with reporting privileges. Password and OTP verification are complete; any required first-login password change is complete. Select an explicit authorized report scope and both inclusive date bounds.

**Parameters:**  Reversed dates; format xlsx.

**Steps:** 1: Generate with start 30 June 2026 and end 1 June 2026. 2: Request export format 'xlsx'.

**Expected result:** The reversed range is rejected with a validation message; xlsx is rejected as unsupported; no file is produced.

**Actual result:** Fresh execution: 2 mapped test method(s) passed. Assertions cover the automated equivalent described by the named methods; this is not a claim of a separate literal manual execution.

**Result:** PASS automated equivalent

**Evidence:** `evidence/part3-2026-11-06/regression.json` (archived)

**Exact test methods:**

- `tests.test_report_scope.ReportScopeTests.test_unsupported_export_format_does_not_produce_a_file`
- `apps.attendance.test_backlog_suhas.BacklogFeatureTests.test_student_report_rejects_reversed_date_range`

**Qualification:** Automated equivalent using isolated synthetic fixtures; literal manual example accounts and counts were not separately executed.

## IT_09_1  Verify report figures match the students' own attendance views.

**Module:** Reporting / BL-20, BL-21

**Preconditions:** User is logged in with reporting privileges. Password and OTP verification are complete; any required first-login password change is complete. Select an explicit authorized report scope and both inclusive date bounds.

**Parameters:**  Fixture data.

**Steps:** 1: Generate the CS101 Section A report. 2: Compare each row with that student's My attendance page.

**Expected result:** Every row matches exactly (e.g. S001 74/100 (74.00%)), because both use the same calculation (BL-14).

**Actual result:** Fresh execution: 2 mapped test method(s) passed. Assertions cover the automated equivalent described by the named methods; this is not a claim of a separate literal manual execution.

**Result:** PASS automated equivalent

**Evidence:** `evidence/part3-2026-11-06/regression.json` (archived)

**Exact test methods:**

- `tests.test_integration.ProvisionedAttendanceJourneyTests.test_provisioned_accounts_complete_otp_then_corrected_totals_agree_everywhere`
- `tests.test_integration.AttendanceAlertAndReportIntegrationTests.test_exports_are_private_audited_and_invalid_or_empty_exports_are_not_downloads`

**Qualification:** Automated equivalent using isolated synthetic fixtures; literal manual example accounts and counts were not separately executed.

## IT_09_2  Verify Students cannot generate reports and Faculty only for their own classes (SEC-13, SEC-24).

**Module:** Reporting / BL-20, BL-21

**Preconditions:** S001 and F002 are logged in (separate browsers). Password and OTP verification are complete; any required first-login password change is complete. Select an explicit authorized report scope and both inclusive date bounds.

**Parameters:**  S001; F002; CS101 Section A (F001's class).

**Steps:** 1: As S001, open Reports. 2: As F002, request a CS101 Section A report.

**Expected result:** S001 gets 'Access denied'; F002's request is refused; nothing is exported; the denials are logged.

**Actual result:** Fresh execution: 2 mapped test method(s) passed. Assertions cover the automated equivalent described by the named methods; this is not a claim of a separate literal manual execution.

**Result:** PASS automated equivalent

**Evidence:** `evidence/part3-2026-11-06/regression.json` (archived)

**Exact test methods:**

- `tests.test_integration.AuthorizationIntegrationTests.test_faculty_cannot_read_export_or_modify_another_class`
- `tests.test_integration.AuthorizationIntegrationTests.test_student_cannot_open_admin_faculty_or_another_students_resources`

**Qualification:** Automated equivalent using isolated synthetic fixtures; literal manual example accounts and counts were not separately executed.

## IT_09_3  Verify exports reflect saved data consistently after logout and login.

**Module:** Reporting / BL-20, BL-21

**Preconditions:** User is logged in with reporting privileges. Password and OTP verification are complete; any required first-login password change is complete. Select an explicit authorized report scope and both inclusive date bounds.

**Parameters:**  CSV export.

**Steps:** 1: Export the CS101 Section A report as CSV. 2: Log out and log in. 3: Export it again.

**Expected result:** Both files contain the same rows and totals; each export is logged.

**Actual result:** Fresh execution: 2 mapped test method(s) passed. Assertions cover the automated equivalent described by the named methods; this is not a claim of a separate literal manual execution.

**Result:** PASS automated equivalent

**Evidence:** `evidence/part3-2026-11-06/regression.json` (archived)

**Exact test methods:**

- `tests.test_integration.ProvisionedAttendanceJourneyTests.test_provisioned_accounts_complete_otp_then_corrected_totals_agree_everywhere`
- `tests.test_integration.AttendanceAlertAndReportIntegrationTests.test_exports_are_private_audited_and_invalid_or_empty_exports_are_not_downloads`

**Qualification:** Automated equivalent using isolated synthetic fixtures; literal manual example accounts and counts were not separately executed.

## ST_09_1  End-to-end system test: complete the full "Generate & Export Reports" workflow as an actual user would.

**Module:** Reporting / BL-20, BL-21

**Preconditions:** User is logged in with reporting privileges. Password and OTP verification are complete; any required first-login password change is complete. Select an explicit authorized report scope and both inclusive date bounds.

**Parameters:**  ADMIN1; CS101 Section A; June 2026; export as PDF and as CSV.

**Steps:** 1: User navigates to the Reports screen. 2: User selects report scope (student/class/subject) and date range. 3: System compiles the report. 4: User exports the report as PDF or CSV. 5: System generates and downloads the file.

**Expected result:** Both files download, open correctly and show S001 74/100, S002 75/100, S004 76/100; CSV cells starting with =, +, - or @ are neutralized; both exports are logged.

**Actual result:** Fresh execution: 2 mapped test method(s) passed. Assertions cover the automated equivalent described by the named methods; this is not a claim of a separate literal manual execution.

**Result:** PASS automated equivalent

**Evidence:** `evidence/part3-2026-11-06/regression.json` (archived)

**Exact test methods:**

- `tests.test_integration.ProvisionedAttendanceJourneyTests.test_provisioned_accounts_complete_otp_then_corrected_totals_agree_everywhere`
- `tests.test_integration.AttendanceAlertAndReportIntegrationTests.test_exports_are_private_audited_and_invalid_or_empty_exports_are_not_downloads`

**Qualification:** Automated equivalent using isolated synthetic fixtures; literal manual example accounts and counts were not separately executed.

## ST_09_2  System test: verify the exception flow  -  Selected date range has no data: system shows a message instead of an empty file.

**Module:** Reporting / BL-20, BL-21

**Preconditions:** User is logged in with reporting privileges. Password and OTP verification are complete; any required first-login password change is complete. Select an explicit authorized report scope and both inclusive date bounds.

**Parameters:**  A range with no sessions.

**Steps:** 1: Choose CS101 Section A with dates 1 to 31 Dec 2026. 2: Generate.

**Expected result:** A 'no data for this selection' message is shown and no file is produced.

**Actual result:** Fresh execution: 1 mapped test method(s) passed. Assertions cover the automated equivalent described by the named methods; this is not a claim of a separate literal manual execution.

**Result:** PASS automated equivalent

**Evidence:** `evidence/part3-2026-11-06/regression.json` (archived)

**Exact test methods:**

- `tests.test_integration.AttendanceAlertAndReportIntegrationTests.test_exports_are_private_audited_and_invalid_or_empty_exports_are_not_downloads`

**Qualification:** Automated equivalent using isolated synthetic fixtures; literal manual example accounts and counts were not separately executed.

## UT_10_1  Verify Low Attendance Detection & Notification succeeds with valid input.

**Module:** Attendance Monitoring / BL-22, BL-23, BL-24

**Preconditions:** Attendance threshold is configured by the Admin (default 75%).

**Parameters:**  Threshold 75%; S1 Subject A 74/99 (74.75%).

**Steps:** 1: System recalculates percentages after an attendance save. 2: System compares the exact subject and overall percentages with the threshold. 3: System flags percentages below the threshold.

**Expected result:** S1 is flagged for Subject A.

**Actual result:** Fresh execution: 1 mapped test method(s) passed. Assertions cover the automated equivalent described by the named methods; this is not a claim of a separate literal manual execution.

**Result:** PASS automated equivalent

**Evidence:** `evidence/part3-2026-11-06/regression.json` (archived)

**Exact test methods:**

- `apps.notifications.tests.DetectionTests.test_ut_10_2_below_at_and_above_and_zero`

**Qualification:** Automated equivalent using isolated synthetic fixtures; literal manual example accounts and counts were not separately executed.

## UT_10_2  Verify threshold comparison below, at, and above the threshold.

**Module:** Attendance Monitoring / BL-22

**Preconditions:** Admin threshold is 75%; fixture data is loaded.

**Parameters:**  S001 74/100; S002 75/100; S004 76/100; S003 0/0 (CS101 or MA101).

**Steps:** 1: Evaluate each student's exact attendance ratio. 2: Review subject and overall shortage indicators.

**Expected result:** S001 is flagged; S002 (equal) and S004 (above) are not; S003 with no recorded classes is not flagged.

**Actual result:** Fresh execution: 1 mapped test method(s) passed. Assertions cover the automated equivalent described by the named methods; this is not a claim of a separate literal manual execution.

**Result:** PASS automated equivalent

**Evidence:** `evidence/part3-2026-11-06/regression.json` (archived)

**Exact test methods:**

- `apps.notifications.tests.DetectionTests.test_ut_10_2_below_at_and_above_and_zero`

**Qualification:** Automated equivalent using isolated synthetic fixtures; literal manual example accounts and counts were not separately executed.

## UT_10_3  Verify invalid threshold values are rejected and do not alter the saved setting.

**Module:** Attendance Monitoring / BL-22

**Preconditions:** Admin is logged in; current threshold is 75%. Password and OTP verification are complete; any required first-login password change is complete.

**Parameters:**  0, 101, 74.5, abc, blank.

**Steps:** 1: Open Configure attendance threshold. 2: Submit each invalid value separately. 3: Reload the page.

**Expected result:** Each invalid value is rejected with a validation error; the saved threshold remains 75%.

**Actual result:** Fresh execution: 1 mapped test method(s) passed. Assertions cover the automated equivalent described by the named methods; this is not a claim of a separate literal manual execution.

**Result:** PASS automated equivalent

**Evidence:** `evidence/part3-2026-11-06/regression.json` (archived)

**Exact test methods:**

- `apps.attendance.test_backlog_suhas.BacklogFeatureTests.test_threshold_rejects_values_outside_one_to_one_hundred`

**Qualification:** Automated equivalent using isolated synthetic fixtures; literal manual example accounts and counts were not separately executed.

## UT_10_4  Verify a percentage below the threshold is flagged (AR-12).

**Module:** Attendance Monitoring / BL-22, BL-23, BL-24

**Preconditions:** Attendance threshold is configured by the Admin (default 75%).

**Parameters:**  Threshold 75%; 74/99 (74.75%).

**Steps:** 1: Evaluate S1 Subject A.

**Expected result:** S1 is flagged for Subject A.

**Actual result:** Fresh execution: 1 mapped test method(s) passed. Assertions cover the automated equivalent described by the named methods; this is not a claim of a separate literal manual execution.

**Result:** PASS automated equivalent

**Evidence:** `evidence/part3-2026-11-06/regression.json` (archived)

**Exact test methods:**

- `apps.notifications.tests.DetectionTests.test_ut_10_2_below_at_and_above_and_zero`

**Qualification:** Automated equivalent using isolated synthetic fixtures; literal manual example accounts and counts were not separately executed.

## UT_10_5  Verify a percentage equal to the threshold is not flagged (AR-12).

**Module:** Attendance Monitoring / BL-22, BL-23, BL-24

**Preconditions:** Attendance threshold is configured by the Admin (default 75%).

**Parameters:**  Threshold 75%; 3/4 (75.00%).

**Steps:** 1: Evaluate S1 Subject A.

**Expected result:** S1 is not flagged.

**Actual result:** Fresh execution: 1 mapped test method(s) passed. Assertions cover the automated equivalent described by the named methods; this is not a claim of a separate literal manual execution.

**Result:** PASS automated equivalent

**Evidence:** `evidence/part3-2026-11-06/regression.json` (archived)

**Exact test methods:**

- `apps.notifications.tests.DetectionTests.test_ut_10_2_below_at_and_above_and_zero`

**Qualification:** Automated equivalent using isolated synthetic fixtures; literal manual example accounts and counts were not separately executed.

## UT_10_6  Verify a subject with zero sessions is not flagged (AR-12).

**Module:** Attendance Monitoring / BL-22, BL-23, BL-24

**Preconditions:** Attendance threshold is configured by the Admin (default 75%).

**Parameters:**  Threshold 75%; 0 sessions.

**Steps:** 1: Evaluate S1 Subject C.

**Expected result:** Subject C is not flagged and no notification is sent.

**Actual result:** Fresh execution: 1 mapped test method(s) passed. Assertions cover the automated equivalent described by the named methods; this is not a claim of a separate literal manual execution.

**Result:** PASS automated equivalent

**Evidence:** `evidence/part3-2026-11-06/regression.json` (archived)

**Exact test methods:**

- `apps.notifications.tests.StudentNotificationTests.test_ut_10_6_subject_without_sessions_is_never_flagged`

**Qualification:** Automated equivalent using isolated synthetic fixtures; literal manual example accounts and counts were not separately executed.

## UT_10_7  Verify the comparison uses the exact, unrounded value (AR-12).

**Module:** Attendance Monitoring / BL-22, BL-23, BL-24

**Preconditions:** Attendance threshold is configured by the Admin (default 75%).

**Parameters:**  Threshold 75%; 14,999/20,000 (74.995%).

**Steps:** 1: Evaluate the percentage. 2: Display it.

**Expected result:** Displays 75.00% but is flagged, because 14,999  x  100 < 75  x  20,000.

**Actual result:** Fresh execution: 1 mapped test method(s) passed. Assertions cover the automated equivalent described by the named methods; this is not a claim of a separate literal manual execution.

**Result:** PASS automated equivalent

**Evidence:** `evidence/part3-2026-11-06/regression.json` (archived)

**Exact test methods:**

- `apps.notifications.tests.UnitRuleTests.test_exact_comparison`

**Qualification:** Automated equivalent using isolated synthetic fixtures; literal manual example accounts and counts were not separately executed.

## UT_10_8  Verify subject and overall percentages are evaluated separately (AR-12).

**Module:** Attendance Monitoring / BL-22, BL-23, BL-24

**Preconditions:** Attendance threshold is configured by the Admin (default 75%).

**Parameters:**  Subject A 10/10; Subject B 2/3 (66.67%); overall 12/13 (92.31%).

**Steps:** 1: Evaluate S1.

**Expected result:** Subject B is flagged; overall is not flagged.

**Actual result:** Fresh execution: 1 mapped test method(s) passed. Assertions cover the automated equivalent described by the named methods; this is not a claim of a separate literal manual execution.

**Result:** PASS automated equivalent

**Evidence:** `evidence/part3-2026-11-06/regression.json` (archived)

**Exact test methods:**

- `apps.notifications.tests.DetectionTests.test_ut_10_8_subject_and_overall_evaluated_separately`

**Qualification:** Automated equivalent using isolated synthetic fixtures; literal manual example accounts and counts were not separately executed.

## IT_10_1  Verify shortage counts on the dashboards follow the saved attendance.

**Module:** Attendance Monitoring / BL-22, BL-23, BL-24

**Preconditions:** Attendance threshold is configured by the Admin (default 75%).

**Parameters:**  Fixture data; threshold 75%.

**Steps:** 1: As ADMIN1, open the dashboard. 2: As F001, F002 and F003, open their dashboards.

**Expected result:** Admin: 1 student below overall, 2 subject shortages; F001: 1 and 1 (S001 CS101); F002: 1 and 1 (S001 MA101); F003: 0 and 0.

**Actual result:** Fresh execution: 2 mapped test method(s) passed. Assertions cover the automated equivalent described by the named methods; this is not a claim of a separate literal manual execution.

**Result:** PASS automated equivalent

**Evidence:** `evidence/part3-2026-11-06/regression.json` (archived)

**Exact test methods:**

- `apps.attendance.test_backlog_suhas.BacklogFeatureTests.test_dashboard_statistics_are_role_scoped_and_present`
- `apps.attendance.test_backlog_suhas.BacklogFeatureTests.test_shortage_counts_use_exact_ratio_equality_and_ignore_zero_records`

**Qualification:** Automated equivalent using isolated synthetic fixtures; literal manual example accounts and counts were not separately executed.

## IT_10_2  Verify only the Admin can change the attendance threshold (SEC-14).

**Module:** Attendance Monitoring / BL-22, BL-23, BL-24

**Preconditions:** Faculty F1 and Student S1 accounts exist.

**Parameters:**  F1 and S1 credentials; value 60.

**Steps:** 1: Log in as F1 and try to change the threshold to 60%. 2: Repeat as S1.

**Expected result:** Both attempts are denied; the threshold stays at 75%; the denials are logged.

**Actual result:** Fresh execution: 1 mapped test method(s) passed. Assertions cover the automated equivalent described by the named methods; this is not a claim of a separate literal manual execution.

**Result:** PASS automated equivalent

**Evidence:** `evidence/part3-2026-11-06/regression.json` (archived)

**Exact test methods:**

- `apps.attendance.test_backlog_suhas.BacklogFeatureTests.test_only_admin_can_change_threshold`

**Qualification:** Automated equivalent using isolated synthetic fixtures; literal manual example accounts and counts were not separately executed.

## IT_10_3  Verify a saved threshold persists after logout and login and changes the counts.

**Module:** Attendance Monitoring / BL-22, BL-23, BL-24

**Preconditions:** Attendance threshold is configured by the Admin (default 75%).

**Parameters:**  Threshold 80.

**Steps:** 1: As ADMIN1, set the threshold to 80. 2: Log out and log in. 3: Open the threshold page and the dashboard.

**Expected result:** The setting shows 80%; the dashboard shows 3 students below overall (S001, S002, S004) and 4 subject shortages; the change is logged.

**Actual result:** Fresh execution: 1 mapped test method(s) passed. Assertions cover the automated equivalent described by the named methods; this is not a claim of a separate literal manual execution.

**Result:** PASS automated equivalent

**Evidence:** `evidence/part3-2026-11-06/regression.json` (archived)

**Exact test methods:**

- `apps.attendance.test_backlog_suhas.BacklogFeatureTests.test_threshold_defaults_to_75_and_admin_can_change_it`

**Qualification:** Automated equivalent using isolated synthetic fixtures; literal manual example accounts and counts were not separately executed.

## IT_10_4  Verify a threshold change re-evaluates all students (AR-13).

**Module:** Attendance Monitoring / BL-22, BL-23, BL-24

**Preconditions:** Threshold 75%; S1 Subject A at 78/100 (78.00%) and not flagged.

**Parameters:**  New threshold 80%.

**Steps:** 1: As Admin, change the threshold to 80%. 2: Check S1's flag and notifications.

**Expected result:** S1 is flagged for Subject A and receives one in-app notification and one email.

**Actual result:** Fresh execution: 1 mapped test method(s) passed. Assertions cover the automated equivalent described by the named methods; this is not a claim of a separate literal manual execution.

**Result:** PASS automated equivalent

**Evidence:** `evidence/part3-2026-11-06/regression.json` (archived)

**Exact test methods:**

- `apps.notifications.tests.StudentNotificationTests.test_it_10_4_threshold_change_re_evaluates_everyone_once`

**Qualification:** Automated equivalent using isolated synthetic fixtures; literal manual example accounts and counts were not separately executed.

## IT_10_5  Verify an email failure does not block the in-app notification (AR-13).

**Module:** Attendance Monitoring / BL-22, BL-23, BL-24

**Preconditions:** The email service is unavailable.

**Parameters:**  S1 Subject A: 75/100  >  75/101.

**Steps:** 1: Record an absence that takes S1 below 75%. 2: Check S1's in-app notifications and the logs.

**Expected result:** The in-app notification is delivered; the email failure is logged.

**Actual result:** Fresh execution: 1 mapped test method(s) passed. Assertions cover the automated equivalent described by the named methods; this is not a claim of a separate literal manual execution.

**Result:** PASS automated equivalent

**Evidence:** `evidence/part3-2026-11-06/regression.json` (archived)

**Exact test methods:**

- `apps.notifications.tests.StudentNotificationTests.test_it_10_5_email_failure_still_delivers_in_app_and_is_logged`

**Qualification:** Automated equivalent using isolated synthetic fixtures; literal manual example accounts and counts were not separately executed.

## ST_10_1  End-to-end system test: complete the full "Low Attendance Detection & Notification" workflow as an actual user would.

**Module:** Attendance Monitoring / BL-22, BL-23, BL-24

**Preconditions:** Attendance threshold is configured by the Admin (default 75%).

**Parameters:**  Threshold 75%; S1 Subject A moves from 75/99 to 75/100 (75.00%) and then to 75/101 (74.26%).

**Steps:** 1: System recalculates percentages after every save or correction. 2: System compares exact percentages with the threshold. 3: System flags percentages below the threshold. 4: System sends the student one in-app notification and one email. 5: Faculty/Admin view the below-threshold list.

**Expected result:** At 75.00% S1 is not flagged and no notification is sent; at 74.26% S1 is flagged, receives exactly one in-app notification and one email, and appears on the faculty list.

**Actual result:** Fresh execution: 1 mapped test method(s) passed. Assertions cover the automated equivalent described by the named methods; this is not a claim of a separate literal manual execution.

**Result:** PASS automated equivalent

**Evidence:** `evidence/part3-2026-11-06/regression.json` (archived)

**Exact test methods:**

- `apps.notifications.tests.StudentNotificationTests.test_st_10_1_equal_is_silent_then_one_drop_one_notification_and_email`

**Qualification:** Automated equivalent using isolated synthetic fixtures; literal manual example accounts and counts were not separately executed.

## ST_10_2  System test: verify the exception flow  -  Student's attendance recovers to or above the threshold: system clears the flag and sends no further notifications.

**Module:** Attendance Monitoring / BL-22, BL-23, BL-24

**Preconditions:** Attendance threshold is configured by the Admin (default 75%).

**Parameters:**  S1 Subject A: 74/99  >  77/102 (75.49%).

**Steps:** 1: Start with S1 flagged at 74/99. 2: Record S1 Present for the next 3 sessions. 3: Check notifications and the below-threshold list.

**Expected result:** The flag is cleared; no notification is sent; S1 is removed from the below-threshold list.

**Actual result:** Fresh execution: 1 mapped test method(s) passed. Assertions cover the automated equivalent described by the named methods; this is not a claim of a separate literal manual execution.

**Result:** PASS automated equivalent

**Evidence:** `evidence/part3-2026-11-06/regression.json` (archived)

**Exact test methods:**

- `apps.notifications.tests.StudentNotificationTests.test_st_10_2_and_st_10_4_recovery_clears_flag_and_next_drop_notifies_again`

**Qualification:** Automated equivalent using isolated synthetic fixtures; literal manual example accounts and counts were not separately executed.

## ST_10_3  Verify no repeat notification while a student stays below the threshold (AR-13).

**Module:** Attendance Monitoring / BL-22, BL-23, BL-24

**Preconditions:** S1 is already flagged for Subject A at 74/99 and was notified once.

**Parameters:**  S1 Subject A: 74/99  >  74/101.

**Steps:** 1: Record S1 Absent for 2 more sessions. 2: Check S1's notifications.

**Expected result:** No new notification is sent; S1 remains flagged.

**Actual result:** Fresh execution: 1 mapped test method(s) passed. Assertions cover the automated equivalent described by the named methods; this is not a claim of a separate literal manual execution.

**Result:** PASS automated equivalent

**Evidence:** `evidence/part3-2026-11-06/regression.json` (archived)

**Exact test methods:**

- `apps.notifications.tests.StudentNotificationTests.test_st_10_3_no_repeat_while_below`

**Qualification:** Automated equivalent using isolated synthetic fixtures; literal manual example accounts and counts were not separately executed.

## ST_10_4  Verify a new drop after recovery sends a new notification (AR-13).

**Module:** Attendance Monitoring / BL-22, BL-23, BL-24

**Preconditions:** S1 recovered to 77/102 (75.49%) after an earlier notification.

**Parameters:**  S1 Subject A: 77/102  >  77/103 (74.76%).

**Steps:** 1: Record S1 Absent until Subject A falls below 75%. 2: Check notifications.

**Expected result:** Exactly one new in-app notification and one email are sent.

**Actual result:** Fresh execution: 1 mapped test method(s) passed. Assertions cover the automated equivalent described by the named methods; this is not a claim of a separate literal manual execution.

**Result:** PASS automated equivalent

**Evidence:** `evidence/part3-2026-11-06/regression.json` (archived)

**Exact test methods:**

- `apps.notifications.tests.StudentNotificationTests.test_st_10_2_and_st_10_4_recovery_clears_flag_and_next_drop_notifies_again`

**Qualification:** Automated equivalent using isolated synthetic fixtures; literal manual example accounts and counts were not separately executed.

## ST_10_5  Verify the Monday faculty email lists only the faculty member's own students below the threshold (AR-14).

**Module:** Attendance Monitoring / BL-22, BL-23, BL-24

**Preconditions:** F1 teaches CS101 (S1 below threshold); F2 teaches CS102 (no students below).

**Parameters:**  Threshold 75%.

**Steps:** 1: Run the Monday 08:00 job. 2: Check F1's and F2's email and in-app lists.

**Expected result:** F1 receives one email listing S1 for CS101 only; F2 receives no email; both in-app lists match.

**Actual result:** Fresh execution: 1 mapped test method(s) passed. Assertions cover the automated equivalent described by the named methods; this is not a claim of a separate literal manual execution.

**Result:** PASS automated equivalent

**Evidence:** `evidence/part3-2026-11-06/regression.json` (archived)

**Exact test methods:**

- `apps.notifications.tests.WeeklyEmailTests.test_st_10_5_each_faculty_gets_only_own_students_and_none_when_empty`

**Qualification:** Automated equivalent using isolated synthetic fixtures; literal manual example accounts and counts were not separately executed.

## ST_10_6  Verify the default threshold of 75% is used when none is configured (UC-10 2a).

**Module:** Attendance Monitoring / BL-22, BL-23, BL-24

**Preconditions:** No threshold has been saved.

**Parameters:**  No configured threshold.

**Steps:** 1: Record attendance that takes S1 to 74/99. 2: Check S1's flag.

**Expected result:** S1 is flagged using the default 75%.

**Actual result:** Fresh execution: 1 mapped test method(s) passed. Assertions cover the automated equivalent described by the named methods; this is not a claim of a separate literal manual execution.

**Result:** PASS automated equivalent

**Evidence:** `evidence/part3-2026-11-06/regression.json` (archived)

**Exact test methods:**

- `apps.notifications.tests.StudentNotificationTests.test_st_10_6_default_threshold_without_saved_setting`

**Qualification:** Automated equivalent using isolated synthetic fixtures; literal manual example accounts and counts were not separately executed.

## IT_10_7  Verify only Admin can change the institution threshold.

**Module:** Attendance Monitoring / BL-22 / SEC-14

**Preconditions:** Admin, Faculty, and Student test accounts exist.

**Parameters:**  POST value=80 for each role.

**Steps:** 1: Log in as Faculty and POST threshold 80. 2: Repeat as Student. 3: Log in as Admin and save 80.

**Expected result:** Faculty and Student receive HTTP 403 and the setting is unchanged; Admin can save 80 successfully.

**Actual result:** Fresh execution: 1 mapped test method(s) passed. Assertions cover the automated equivalent described by the named methods; this is not a claim of a separate literal manual execution.

**Result:** PASS automated equivalent

**Evidence:** `evidence/part3-2026-11-06/regression.json` (archived)

**Exact test methods:**

- `apps.attendance.test_backlog_suhas.BacklogFeatureTests.test_only_admin_can_change_threshold`

**Qualification:** Automated equivalent using isolated synthetic fixtures; literal manual example accounts and counts were not separately executed.

## IT_10_6  Verify shortage evaluation updates after attendance correction and threshold change.

**Module:** Attendance Monitoring / BL-22

**Preconditions:** Student S001 has 74/100 attendance; current threshold is 75%.

**Parameters:**  Threshold 75%, then 76%; ratios 74/100 and 75/100.

**Steps:** 1: Confirm shortage. 2: Correct one Absent record to Present to reach 75/100. 3: Change threshold to 76%.

**Expected result:** At 74% S001 is flagged at 75%; at exactly 75% S001 is not flagged at 75%; after threshold changes to 76%, S001 is flagged again.

**Actual result:** Fresh execution: 1 mapped test method(s) passed. Assertions cover the automated equivalent described by the named methods; this is not a claim of a separate literal manual execution.

**Result:** PASS automated equivalent

**Evidence:** `evidence/part3-2026-11-06/regression.json` (archived)

**Exact test methods:**

- `apps.notifications.tests.StudentNotificationTests.test_it_10_6_correction_recovers_then_threshold_change_flags_again`

**Qualification:** Automated equivalent using isolated synthetic fixtures; literal manual example accounts and counts were not separately executed.

## UT_11_1  Verify Search & Filter Records succeeds with valid input.

**Module:** Search & Filter / BL-19

**Preconditions:** User is logged in and viewing a record list. Password and OTP verification are complete; any required first-login password change is complete.

**Parameters:**  F001; filters: subject CS101, student S002, 1 to 30 June 2026.

**Steps:** 1: User enters a search term or applies filters (student, subject, date, class). 2: System queries matching attendance records. 3: System displays the filtered result set.

**Expected result:** Exactly S002's 100 CS101 records are listed (75 Present, 25 Absent).

**Actual result:** Fresh execution: 2 mapped test method(s) passed. Assertions cover the automated equivalent described by the named methods; this is not a claim of a separate literal manual execution.

**Result:** PASS automated equivalent

**Evidence:** `evidence/part3-2026-11-06/regression.json` (archived)

**Exact test methods:**

- `apps.attendance.test_history.AttendanceHistoryTests.test_each_optional_filter_narrows_records`
- `apps.attendance.test_history.AttendanceHistoryTests.test_filter_dates_are_inclusive_and_filters_combine`

**Qualification:** Automated equivalent using isolated synthetic fixtures; literal manual example accounts and counts were not separately executed.

## UT_11_2  Verify an end date earlier than the start date is rejected (UC-11 1a).

**Module:** Search & Filter / BL-19

**Preconditions:** User is logged in and viewing a record list. Password and OTP verification are complete; any required first-login password change is complete.

**Parameters:**  Reversed date range.

**Steps:** 1: Open Search. 2: Enter start 30 June 2026 and end 1 June 2026. 3: Search.

**Expected result:** A validation message asks for a valid date range; no results are shown.

**Actual result:** Fresh execution: 1 mapped test method(s) passed. Assertions cover the automated equivalent described by the named methods; this is not a claim of a separate literal manual execution.

**Result:** PASS automated equivalent

**Evidence:** `evidence/part3-2026-11-06/regression.json` (archived)

**Exact test methods:**

- `apps.attendance.test_history.AttendanceHistoryTests.test_invalid_filters_show_errors_without_returning_unfiltered_records`

**Qualification:** Automated equivalent using isolated synthetic fixtures; literal manual example accounts and counts were not separately executed.

## UT_11_3  Verify filters outside the user's scope reveal nothing.

**Module:** Search & Filter / BL-19

**Preconditions:** User is logged in and viewing a record list. Password and OTP verification are complete; any required first-login password change is complete.

**Parameters:**  S003 and MA101 are outside F001's classes.

**Steps:** 1: As F001, search for student S003. 2: Edit the request to use MA101's subject ID.

**Expected result:** No records are returned in either case; no data about S003 or MA101 is shown.

**Actual result:** Fresh execution: 1 mapped test method(s) passed. Assertions cover the automated equivalent described by the named methods; this is not a claim of a separate literal manual execution.

**Result:** PASS automated equivalent

**Evidence:** `evidence/part3-2026-11-06/regression.json` (archived)

**Exact test methods:**

- `apps.attendance.test_history.AttendanceHistoryTests.test_foreign_filter_ids_return_logged_403_without_leaking_rows`

**Qualification:** Automated equivalent using isolated synthetic fixtures; literal manual example accounts and counts were not separately executed.

## IT_11_1  Verify search results match the attendance views.

**Module:** Search & Filter / BL-19

**Preconditions:** User is logged in and viewing a record list. Password and OTP verification are complete; any required first-login password change is complete.

**Parameters:**  S001, MA101.

**Steps:** 1: As ADMIN1, search student S001, subject MA101. 2: Compare with S001's My attendance page.

**Expected result:** 3 records (1 Oct Present, 2 Oct Absent, 3 Oct Present), matching MA101 2/3 (66.67%).

**Actual result:** Fresh execution: 2 mapped test method(s) passed. Assertions cover the automated equivalent described by the named methods; this is not a claim of a separate literal manual execution.

**Result:** PASS automated equivalent

**Evidence:** `evidence/part3-2026-11-06/regression.json` (archived)

**Exact test methods:**

- `apps.attendance.test_history.AttendanceHistoryTests.test_each_optional_filter_narrows_records`
- `apps.attendance.test_history.AttendanceHistoryTests.test_filter_dates_are_inclusive_and_filters_combine`

**Qualification:** Automated equivalent using isolated synthetic fixtures; literal manual example accounts and counts were not separately executed.

## IT_11_2  Verify Students cannot search records and Faculty see only their own classes (SEC-13).

**Module:** Search & Filter / BL-19

**Preconditions:** S001 and F002 are logged in (separate browsers). Password and OTP verification are complete; any required first-login password change is complete.

**Parameters:**  S001; F002.

**Steps:** 1: As S001, open Search. 2: As F002, search subject CS101.

**Expected result:** S001 gets 'Access denied'; F002's results contain no CS101 Section A records.

**Actual result:** Fresh execution: 2 mapped test method(s) passed. Assertions cover the automated equivalent described by the named methods; this is not a claim of a separate literal manual execution.

**Result:** PASS automated equivalent

**Evidence:** `evidence/part3-2026-11-06/regression.json` (archived)

**Exact test methods:**

- `apps.attendance.test_history.AttendanceHistoryTests.test_students_cannot_open_history_including_their_own_changes`
- `apps.attendance.test_history.AttendanceHistoryTests.test_faculty_sees_only_assigned_records_and_filter_choices`

**Qualification:** Automated equivalent using isolated synthetic fixtures; literal manual example accounts and counts were not separately executed.

## IT_11_3  Verify search results reflect a correction after logout and login.

**Module:** Search & Filter / BL-19

**Preconditions:** User is logged in and viewing a record list. Password and OTP verification are complete; any required first-login password change is complete.

**Parameters:**  S001 MA101, 2 Oct: Absent  >  Present.

**Steps:** 1: Correct S001's 2 Oct MA101 record to Present. 2: Log out and log in. 3: Search S001, MA101.

**Expected result:** The 2 Oct record shows Present and MA101 totals show 3/3 (100.00%).

**Actual result:** Fresh execution: 1 mapped test method(s) passed. Assertions cover the automated equivalent described by the named methods; this is not a claim of a separate literal manual execution.

**Result:** PASS automated equivalent

**Evidence:** `evidence/part3-2026-11-06/regression.json` (archived)

**Exact test methods:**

- `apps.attendance.test_history.AttendanceHistoryTests.test_current_status_and_corrections_persist_after_relogin`

**Qualification:** Automated equivalent using isolated synthetic fixtures; literal manual example accounts and counts were not separately executed.

## ST_11_1  End-to-end system test: complete the full "Search & Filter Records" workflow as an actual user would.

**Module:** Search & Filter / BL-19

**Preconditions:** User is logged in and viewing a record list. Password and OTP verification are complete; any required first-login password change is complete.

**Parameters:**  F001; subject CS101; student S004; June 2026.

**Steps:** 1: User enters a search term or applies filters (student, subject, date, class). 2: System queries matching attendance records. 3: System displays the filtered result set.

**Expected result:** Exactly S004's 100 CS101 records are listed (76 Present); the totals match S004's attendance view.

**Actual result:** Fresh execution: 2 mapped test method(s) passed. Assertions cover the automated equivalent described by the named methods; this is not a claim of a separate literal manual execution.

**Result:** PASS automated equivalent

**Evidence:** `evidence/part3-2026-11-06/regression.json` (archived)

**Exact test methods:**

- `apps.attendance.test_history.AttendanceHistoryTests.test_each_optional_filter_narrows_records`
- `apps.attendance.test_history.AttendanceHistoryTests.test_filter_dates_are_inclusive_and_filters_combine`

**Qualification:** Automated equivalent using isolated synthetic fixtures; literal manual example accounts and counts were not separately executed.

## ST_11_2  System test: verify the exception flow  -  No records match the filter: system shows a 'no results' message.

**Module:** Search & Filter / BL-19

**Preconditions:** User is logged in and viewing a record list. Password and OTP verification are complete; any required first-login password change is complete.

**Parameters:**  S003 has no CS101 records.

**Steps:** 1: As ADMIN1, search for student S003 in CS101.

**Expected result:** A 'no results' message is shown.

**Actual result:** Fresh execution: 1 mapped test method(s) passed. Assertions cover the automated equivalent described by the named methods; this is not a claim of a separate literal manual execution.

**Result:** PASS automated equivalent

**Evidence:** `evidence/part3-2026-11-06/regression.json` (archived)

**Exact test methods:**

- `apps.attendance.test_history.AttendanceHistoryTests.test_empty_history_has_clear_message`

**Qualification:** Automated equivalent using isolated synthetic fixtures; literal manual example accounts and counts were not separately executed.

## UT_12_1  Verify Dashboard & Logout succeeds with valid input.

**Module:** Dashboard / Session / BL-06, BL-25

**Preconditions:** User is logged in. Password and OTP verification are complete; any required first-login password change is complete.

**Parameters:**  S001 / Attend#2026.

**Steps:** 1: System displays a role-specific dashboard with key attendance statistics on login. 2: User reviews summary widgets (e.g., overall %, shortage count, recent activity). 3: User clicks Logout.

**Expected result:** The Student dashboard shows overall 76/103 (73.79%), threshold 75% and 'Your overall attendance is below the threshold.'; Log out returns to the login page with 'You have been logged out.'

**Actual result:** Fresh execution: 2 mapped test method(s) passed. Assertions cover the automated equivalent described by the named methods; this is not a claim of a separate literal manual execution.

**Result:** PASS automated equivalent

**Evidence:** `evidence/part3-2026-11-06/regression.json` (archived)

**Exact test methods:**

- `apps.attendance.test_summary.StudentAttendanceSummaryTests.test_subject_and_overall_counts_are_displayed`
- `apps.accounts.test_sessions.LogoutAndSessionTests.test_logout_invalidates_session_and_returns_to_login`

**Qualification:** Automated equivalent using isolated synthetic fixtures; literal manual example accounts and counts were not separately executed.

## UT_12_2  Verify each role receives only its own dashboard and permitted statistics.

**Module:** Dashboard / Session / BL-25

**Preconditions:** Admin, Faculty F001, and Student S001 test accounts exist; F001 teaches section A only.

**Parameters:**  Admin has all records; F001 has section A; S001 has own attendance only.

**Steps:** 1: Log in as each role. 2: Inspect dashboard metrics. 3: Attempt to open another role's dashboard directly.

**Expected result:** Each login redirects to the matching dashboard; Faculty metrics include only assigned classes; Student metrics include only own attendance; cross-role dashboard requests return HTTP 403.

**Actual result:** Fresh execution: 2 mapped test method(s) passed. Assertions cover the automated equivalent described by the named methods; this is not a claim of a separate literal manual execution.

**Result:** PASS automated equivalent

**Evidence:** `evidence/part3-2026-11-06/regression.json` (archived)

**Exact test methods:**

- `apps.attendance.test_backlog_suhas.BacklogFeatureTests.test_dashboard_statistics_are_role_scoped_and_present`
- `apps.accounts.test_permissions.DenialTests.test_role_dashboards_deny_other_roles`

**Qualification:** Automated equivalent using isolated synthetic fixtures; literal manual example accounts and counts were not separately executed.

## UT_12_3  Verify dashboards clearly represent a no-data state.

**Module:** Dashboard / Session / BL-25

**Preconditions:** Fixture data: F003 has no classes; S003 has no recorded classes.

**Parameters:**  F003 and S003 / Attend#2026.

**Steps:** 1: Sign in as each role. 2: Review counts and attendance widgets.

**Expected result:** F003's dashboard shows 0 classes, 0 students, 0 sessions and 0 shortages; S003's shows 'N/A - no classes yet' and S003 is not flagged.

**Actual result:** Fresh execution: 2 mapped test method(s) passed. Assertions cover the automated equivalent described by the named methods; this is not a claim of a separate literal manual execution.

**Result:** PASS automated equivalent

**Evidence:** `evidence/part3-2026-11-06/regression.json` (archived)

**Exact test methods:**

- `apps.academics.test_teaching_assignments.TeachingAssignmentTests.test_faculty_without_classes_sees_empty_message`
- `apps.attendance.test_calculations.AttendanceCalculationTests.test_enrolled_subjects_without_classes_and_overall_are_na`

**Qualification:** Automated equivalent using isolated synthetic fixtures; literal manual example accounts and counts were not separately executed.

## IT_12_1  Verify dashboards update after a new attendance session.

**Module:** Dashboard / Session / BL-06, BL-25

**Preconditions:** User is logged in. Password and OTP verification are complete; any required first-login password change is complete.

**Parameters:**  One new session.

**Steps:** 1: Note the Admin dashboard's session count (103). 2: As F001, save a CS101 session for today. 3: Reload the Admin dashboard.

**Expected result:** The session count becomes 104 immediately.

**Actual result:** Fresh execution: 1 mapped test method(s) passed. Assertions cover the automated equivalent described by the named methods; this is not a claim of a separate literal manual execution.

**Result:** PASS automated equivalent

**Evidence:** `evidence/part3-2026-11-06/regression.json` (archived)

**Exact test methods:**

- `apps.attendance.test_corrections.AttendanceCorrectionTests.test_saved_correction_updates_calculations_and_all_dashboards`

**Qualification:** Automated equivalent using isolated synthetic fixtures; literal manual example accounts and counts were not separately executed.

## IT_12_2  Verify another role's dashboard URL is refused (SEC-10).

**Module:** Dashboard / Session / BL-06, BL-25

**Preconditions:** F001 is logged in. Password and OTP verification are complete; any required first-login password change is complete.

**Parameters:**  F001.

**Steps:** 1: Open /dashboard/admin/. 2: Open /dashboard/student/. 3: Open /dashboard/faculty/.

**Expected result:** Steps 1 and 2 show 'Access denied' (403) and are logged; step 3 shows F001's own dashboard.

**Actual result:** Fresh execution: 2 mapped test method(s) passed. Assertions cover the automated equivalent described by the named methods; this is not a claim of a separate literal manual execution.

**Result:** PASS automated equivalent

**Evidence:** `evidence/part3-2026-11-06/regression.json` (archived)

**Exact test methods:**

- `apps.attendance.test_backlog_suhas.BacklogFeatureTests.test_dashboard_statistics_are_role_scoped_and_present`
- `apps.accounts.test_permissions.DenialTests.test_role_dashboards_deny_other_roles`

**Qualification:** Automated equivalent using isolated synthetic fixtures; literal manual example accounts and counts were not separately executed.

## IT_12_3  Verify logout ends the session even if an old page is revisited.

**Module:** Dashboard / Session / BL-06, BL-25

**Preconditions:** User is logged in. Password and OTP verification are complete; any required first-login password change is complete.

**Parameters:**  S001.

**Steps:** 1: As S001, open the dashboard. 2: Log out. 3: Press the browser's Back button and reload.

**Expected result:** The dashboard is not shown again; the login page appears; the old session no longer works.

**Actual result:** Fresh execution: 1 mapped test method(s) passed. Assertions cover the automated equivalent described by the named methods; this is not a claim of a separate literal manual execution.

**Result:** PASS automated equivalent

**Evidence:** `evidence/part3-2026-11-06/regression.json` (archived)

**Exact test methods:**

- `apps.accounts.test_sessions.LogoutAndSessionTests.test_protected_pages_reject_previous_session_after_logout`

**Qualification:** Automated equivalent using isolated synthetic fixtures; literal manual example accounts and counts were not separately executed.

## ST_12_1  End-to-end system test: complete the full "Dashboard & Logout" workflow as an actual user would.

**Module:** Dashboard / Session / BL-06, BL-25

**Preconditions:** User is logged in. Password and OTP verification are complete; any required first-login password change is complete.

**Parameters:**  ADMIN1, F001, S001 / Attend#2026.

**Steps:** 1: System displays a role-specific dashboard with key attendance statistics on login. 2: User reviews summary widgets (e.g., overall %, shortage count, recent activity). 3: User clicks Logout. 4: System ends the session and redirects to the login page.

**Expected result:** Admin: 4 students, 3 faculty, 2 sections, 103 sessions; F001: 1 class, 3 students, 100 sessions; S001: overall 76/103 (73.79%). Log out returns to the login page.

**Actual result:** Fresh execution: 2 mapped test method(s) passed. Assertions cover the automated equivalent described by the named methods; this is not a claim of a separate literal manual execution.

**Result:** PASS automated equivalent

**Evidence:** `evidence/part3-2026-11-06/regression.json` (archived)

**Exact test methods:**

- `apps.attendance.test_summary.StudentAttendanceSummaryTests.test_subject_and_overall_counts_are_displayed`
- `apps.accounts.test_sessions.LogoutAndSessionTests.test_logout_invalidates_session_and_returns_to_login`

**Qualification:** Automated equivalent using isolated synthetic fixtures; literal manual example accounts and counts were not separately executed.

## ST_12_2  System test: verify the exception flow  -  Session times out due to inactivity: system logs the user out automatically.

**Module:** Dashboard / Session / BL-06, BL-25

**Preconditions:** User is logged in. Password and OTP verification are complete; any required first-login password change is complete.

**Parameters:**  No activity for 15 minutes (SEC-08).

**Steps:** 1: Log in. 2: Leave the session idle for 15 minutes. 3: Click any link.

**Expected result:** The next request returns to the login page; the old session cannot be reused.

**Actual result:** Fresh execution: 1 mapped test method(s) passed. Assertions cover the automated equivalent described by the named methods; this is not a claim of a separate literal manual execution.

**Result:** PASS automated equivalent

**Evidence:** `evidence/part3-2026-11-06/regression.json` (archived)

**Exact test methods:**

- `apps.accounts.test_sessions.LogoutAndSessionTests.test_session_expires_after_inactivity_and_relogin_works`

**Qualification:** Automated equivalent using isolated synthetic fixtures; literal manual example accounts and counts were not separately executed.

## ST_12_3  Verify attendance changes update dashboard statistics.

**Module:** Dashboard / BL-25 / FR-17 / UC-12

**Preconditions:** Student S001 has one saved attendance record and dashboard is available.

**Parameters:**  Change S001 from Absent to Present.

**Steps:** 1: Load dashboard. 2: Change the saved attendance status using the authorized test workflow. 3: Reload dashboard.

**Expected result:** The overall percentage and shortage indicators reflect the latest saved record without stale cached values.

**Actual result:** Fresh execution: 1 mapped test method(s) passed. Assertions cover the automated equivalent described by the named methods; this is not a claim of a separate literal manual execution.

**Result:** PASS automated equivalent

**Evidence:** `evidence/part3-2026-11-06/regression.json` (archived)

**Exact test methods:**

- `apps.attendance.test_corrections.AttendanceCorrectionTests.test_saved_correction_updates_calculations_and_all_dashboards`

**Qualification:** Automated equivalent using isolated synthetic fixtures; literal manual example accounts and counts were not separately executed.

## UT_13_1  Verify Data Backup & Recovery succeeds with valid input.

**Module:** Backup & Recovery / BL-26, BL-27

**Preconditions:** Admin is logged in with backup/recovery privileges. Password and OTP verification are complete; any required first-login password change is complete.

**Parameters:**  ADMIN1; manual backup of the fixture database.

**Steps:** 1: Admin navigates to the Backup & Recovery screen. 2: Admin initiates a manual backup or configures a scheduled backup. 3: System collects attendance and user data and creates a backup snapshot.

**Expected result:** A backup is created in the encrypted backup store and listed with its time and checksum; the backup is logged.

**Actual result:** Fresh execution: 1 mapped test method(s) passed. Assertions cover the automated equivalent described by the named methods; this is not a claim of a separate literal manual execution.

**Result:** PASS automated equivalent

**Evidence:** `evidence/part3-2026-11-06/regression.json` (archived)

**Exact test methods:**

- `apps.backups.tests.BackupTests.test_manual_backup_has_encrypted_private_file_checksum_and_complete_data`

**Qualification:** Automated equivalent using isolated synthetic fixtures; literal manual example accounts and counts were not separately executed.

## UT_13_2  Verify a backup schedule cannot be saved without a time.

**Module:** Backup & Recovery / BL-26, BL-27

**Preconditions:** Admin is logged in with backup/recovery privileges. Password and OTP verification are complete; any required first-login password change is complete.

**Parameters:**  Blank schedule time.

**Steps:** 1: Open Backup & Recovery  >  Schedule. 2: Leave the time blank. 3: Save.

**Expected result:** A required-field message; no schedule is saved.

**Actual result:** Fresh execution: 1 mapped test method(s) passed. Assertions cover the automated equivalent described by the named methods; this is not a claim of a separate literal manual execution.

**Result:** PASS automated equivalent

**Evidence:** `evidence/part3-2026-11-06/regression.json` (archived)

**Exact test methods:**

- `apps.backups.tests.BackupTests.test_schedule_requires_valid_time_and_admin_can_disable_it`

**Qualification:** Automated equivalent using isolated synthetic fixtures; literal manual example accounts and counts were not separately executed.

## UT_13_3  Verify a corrupted backup is rejected before restore (UC-13 5a, SEC-26).

**Module:** Backup & Recovery / BL-26, BL-27

**Preconditions:** Admin is logged in with backup/recovery privileges. Password and OTP verification are complete; any required first-login password change is complete.

**Parameters:**  Tampered backup file.

**Steps:** 1: Select a backup whose checksum does not match its file. 2: Start a restore and re-enter the Admin password.

**Expected result:** The restore is refused with an integrity error; current data is unchanged; the attempt is logged.

**Actual result:** Fresh execution: 1 mapped test method(s) passed. Assertions cover the automated equivalent described by the named methods; this is not a claim of a separate literal manual execution.

**Result:** PASS automated equivalent

**Evidence:** `evidence/part3-2026-11-06/regression.json` (archived)

**Exact test methods:**

- `apps.backups.tests.BackupTests.test_checksum_corruption_is_rejected_before_safety_backup_or_data_change`

**Qualification:** Automated equivalent using isolated synthetic fixtures; literal manual example accounts and counts were not separately executed.

## IT_13_1  Verify a restore brings back users and attendance with consistent percentages.

**Module:** Backup & Recovery / BL-26, BL-27

**Preconditions:** Admin is logged in with backup/recovery privileges. Password and OTP verification are complete; any required first-login password change is complete.

**Parameters:**  Fixture data; S004 deleted, then restored.

**Steps:** 1: Create a backup. 2: Permanently delete student S004. 3: Restore the backup. 4: Log in as S004.

**Expected result:** S004 can log in again and shows CS101 76/100 (76.00%); all other totals are unchanged.

**Actual result:** Fresh execution: 3 mapped test method(s) passed. Assertions cover the automated equivalent described by the named methods; this is not a claim of a separate literal manual execution.

**Result:** PASS automated equivalent

**Evidence:** `evidence/part3-2026-11-06/regression.json` (archived)

**Exact test methods:**

- `tests.test_integration.BackupRecoveryIntegrationTests.test_encrypted_backup_restores_deleted_account_attendance_alerts_and_login`
- `apps.backups.tests.BackupTests.test_restore_requires_password_and_explicit_confirmation`
- `apps.backups.tests.BackupTests.test_restore_invalidates_sessions_email_and_backup_codes`

**Qualification:** Automated equivalent using isolated synthetic fixtures; literal manual example accounts and counts were not separately executed.

## IT_13_2  Verify only the Admin can back up or restore (SEC-26).

**Module:** Backup & Recovery / BL-26, BL-27

**Preconditions:** F001 and S001 are logged in (separate browsers). Password and OTP verification are complete; any required first-login password change is complete.

**Parameters:**  F001 and S001 credentials.

**Steps:** 1: As F001, open Backup & Recovery and request a restore. 2: Repeat as S001.

**Expected result:** Every request shows 'Access denied'; no backup or restore runs; the denials are logged.

**Actual result:** Fresh execution: 1 mapped test method(s) passed. Assertions cover the automated equivalent described by the named methods; this is not a claim of a separate literal manual execution.

**Result:** PASS automated equivalent

**Evidence:** `evidence/part3-2026-11-06/regression.json` (archived)

**Exact test methods:**

- `apps.backups.tests.BackupTests.test_unauthorized_roles_cannot_list_create_schedule_download_import_or_restore`

**Qualification:** Automated equivalent using isolated synthetic fixtures; literal manual example accounts and counts were not separately executed.

## IT_13_3  Verify the list of backups persists after logout and login.

**Module:** Backup & Recovery / BL-26, BL-27

**Preconditions:** Admin is logged in with backup/recovery privileges. Password and OTP verification are complete; any required first-login password change is complete.

**Parameters:**  One manual backup.

**Steps:** 1: Create a manual backup. 2: Log out and log in. 3: Open Backup & Recovery.

**Expected result:** The backup is listed with its time and checksum.

**Actual result:** Fresh execution: 1 mapped test method(s) passed. Assertions cover the automated equivalent described by the named methods; this is not a claim of a separate literal manual execution.

**Result:** PASS automated equivalent

**Evidence:** `evidence/part3-2026-11-06/regression.json` (archived)

**Exact test methods:**

- `apps.backups.tests.BackupTests.test_backup_list_and_encrypted_download_persist_after_relogin`

**Qualification:** Automated equivalent using isolated synthetic fixtures; literal manual example accounts and counts were not separately executed.

## ST_13_1  End-to-end system test: complete the full "Data Backup & Recovery" workflow as an actual user would.

**Module:** Backup & Recovery / BL-26, BL-27

**Preconditions:** Admin is logged in with backup/recovery privileges. Password and OTP verification are complete; any required first-login password change is complete.

**Parameters:**  ADMIN1; fixture database; one manual backup, then a restore.

**Steps:** 1: Admin navigates to the Backup & Recovery screen. 2: Admin initiates a manual backup or configures a scheduled backup. 3: System collects attendance and user data and creates a backup snapshot. 4: System stores the backup securely and confirms completion to the Admin. 5: Admin selects an existing backup and initiates a restore when needed. Re-enter the Admin password and confirm restoration. Verify integrity/schema and safety backup, atomic restore, retained audit and revocation of old sessions. Log in again using a fresh OTP.

**Expected result:** Backup and restore both complete; the Admin re-enters the password before restoring; afterwards all fixture totals match (e.g. S001 76/103 (73.79%)); both actions are logged. A failed restore rolls back; a successful restore requires fresh authentication and retains the safety backup.

**Actual result:** Fresh execution: 3 mapped test method(s) passed. Assertions cover the automated equivalent described by the named methods; this is not a claim of a separate literal manual execution.

**Result:** PASS automated equivalent

**Evidence:** `evidence/part3-2026-11-06/regression.json` (archived)

**Exact test methods:**

- `tests.test_integration.BackupRecoveryIntegrationTests.test_encrypted_backup_restores_deleted_account_attendance_alerts_and_login`
- `apps.backups.tests.BackupTests.test_restore_requires_password_and_explicit_confirmation`
- `apps.backups.tests.BackupTests.test_restore_invalidates_sessions_email_and_backup_codes`

**Qualification:** Automated equivalent using isolated synthetic fixtures; literal manual example accounts and counts were not separately executed.

## ST_13_2  System test: verify the exception flow  -  Backup process fails (e.g., storage unavailable): system shows an error and retains the last valid backup.

**Module:** Backup & Recovery / BL-26, BL-27

**Preconditions:** Admin is logged in with backup/recovery privileges. Password and OTP verification are complete; any required first-login password change is complete.

**Parameters:**  Unwritable backup location.

**Steps:** 1: Make the backup location unwritable. 2: Start a manual backup.

**Expected result:** An error is shown, the last valid backup is kept, and the failure is logged.

**Actual result:** Fresh execution: 1 mapped test method(s) passed. Assertions cover the automated equivalent described by the named methods; this is not a claim of a separate literal manual execution.

**Result:** PASS automated equivalent

**Evidence:** `evidence/part3-2026-11-06/regression.json` (archived)

**Exact test methods:**

- `apps.backups.tests.BackupTests.test_failed_write_keeps_last_valid_backup_and_logs_failure`

**Qualification:** Automated equivalent using isolated synthetic fixtures; literal manual example accounts and counts were not separately executed.

## PT_01  Measure common authenticated page response time.

**Module:** Performance / NFR-01

**Preconditions:** Use the frozen BL29-v1 plan and an empty guarded local PostgreSQL verification database with 1,000 students, 60 faculty and 750,000 marks.

**Parameters:**  Staging database; 50 concurrent users; no real student data.

**Steps:** Freeze the plan before seeding. Run 50 synchronized users for 30 rounds, then three marking and three semester-export repetitions. Retain each duration, status and source/seed binding.

**Expected result:** At least 95% of measured requests complete within 2 seconds; report percentiles and environment.

**Actual result:** 1500/1500 successful; maximum 0.260 s; p95 0.196 s.

**Result:** PASS local performance profile

**Evidence:** `evidence/part3-2026-11-06/performance.json` (archived)

**Qualification:** Fresh local BL29-v1 performance run on this revision. In-process request stack with loopback PostgreSQL and captured email; deployment transport and external SMTP are excluded.

## PT_02  Measure marking throughput for a 60-student roster.

**Module:** Performance / NFR-01

**Preconditions:** Use the frozen BL29-v1 plan and an empty guarded local PostgreSQL verification database with 1,000 students, 60 faculty and 750,000 marks.

**Parameters:**  60 students; one session; every student Present or Absent.

**Steps:** Freeze the plan before seeding. Run 50 synchronized users for 30 rounds, then three marking and three semester-export repetitions. Retain each duration, status and source/seed binding.

**Expected result:** Successful save completes within 3 seconds; exactly 60 records are persisted.

**Actual result:** 3/3 successful; maximum 0.308 s; p95 0.308 s.

**Result:** PASS local performance profile

**Evidence:** `evidence/part3-2026-11-06/performance.json` (archived)

**Qualification:** Fresh local BL29-v1 performance run on this revision. In-process request stack with loopback PostgreSQL and captured email; deployment transport and external SMTP are excluded.

## PT_03  Measure one-semester section report generation.

**Module:** Performance / NFR-01

**Preconditions:** Use the frozen BL29-v1 plan and an empty guarded local PostgreSQL verification database with 1,000 students, 60 faculty and 750,000 marks.

**Parameters:**  One semester; one section; synthetic student roster.

**Steps:** Freeze the plan before seeding. Run 50 synchronized users for 30 rounds, then three marking and three semester-export repetitions. Retain each duration, status and source/seed binding.

**Expected result:** Report generation completes within 10 seconds.

**Actual result:** 3/3 successful; maximum 0.221 s; p95 0.221 s.

**Result:** PASS local performance profile

**Evidence:** `evidence/part3-2026-11-06/performance.json` (archived)

**Qualification:** Fresh local BL29-v1 performance run on this revision. In-process request stack with loopback PostgreSQL and captured email; deployment transport and external SMTP are excluded.

## PT_04  Check expected data capacity and 50 concurrent users.

**Module:** Capacity / NFR-08

**Preconditions:** Use the frozen BL29-v1 plan and an empty guarded local PostgreSQL verification database with 1,000 students, 60 faculty and 750,000 marks.

**Parameters:**  Synthetic data only; 50 concurrent users.

**Steps:** Freeze the plan before seeding. Run 50 synchronized users for 30 rounds, then three marking and three semester-export repetitions. Retain each duration, status and source/seed binding.

**Expected result:** No data leakage, unhandled server errors, or integrity violations; record latency and resource use.

**Actual result:** 1800 measured requests succeeded; 50 peak in flight; baseline 1,000 students and 750,000 marks.

**Result:** PASS local performance profile

**Evidence:** `evidence/part3-2026-11-06/performance.json` (archived)

**Qualification:** Fresh local BL29-v1 performance run on this revision. In-process request stack with loopback PostgreSQL and captured email; deployment transport and external SMTP are excluded.

## UT_34_1  Student account credentials are mailed only to the owner

**Module:** BL 34 Credential delivery

**Preconditions:** Admin is fully authenticated. Use an isolated database and locally captured email.

**Parameters:**  Fictional owner address; temporary password; configured HTTPS SITE_URL; transport failures where stated.

**Steps:** 1: Prepare the stated recipient/configuration. 2: Trigger the described create/reset/resend operation. 3: Inspect recipients, account state, response and audit without exposing real credentials.

**Expected result:** One owner recipient; no CC/BCC; Admin success is masked; password remains hashed.

**Actual result:** Fresh execution: 1 mapped test method(s) passed. Assertions cover the automated equivalent described by the named methods; this is not a claim of a separate literal manual execution.

**Result:** PASS automated equivalent

**Evidence:** `evidence/part3-2026-11-06/regression.json` (archived)

**Exact test methods:**

- `apps.accounts.test_credential_email.CredentialEmailTests.test_student_creation_emails_only_owner_and_hides_successful_password`

**Qualification:** Automated equivalent using isolated synthetic fixtures; literal manual example accounts and counts were not separately executed.

## UT_34_2  Faculty credentials use the same private delivery policy

**Module:** BL 34 Credential delivery

**Preconditions:** Admin is fully authenticated. Use an isolated database and locally captured email.

**Parameters:**  Fictional owner address; temporary password; configured HTTPS SITE_URL; transport failures where stated.

**Steps:** 1: Prepare the stated recipient/configuration. 2: Trigger the described create/reset/resend operation. 3: Inspect recipients, account state, response and audit without exposing real credentials.

**Expected result:** Only the faculty member receives temporary credentials and the configured login link.

**Actual result:** Fresh execution: 1 mapped test method(s) passed. Assertions cover the automated equivalent described by the named methods; this is not a claim of a separate literal manual execution.

**Result:** PASS automated equivalent

**Evidence:** `evidence/part3-2026-11-06/regression.json` (archived)

**Exact test methods:**

- `apps.accounts.test_credential_email.CredentialEmailTests.test_faculty_creation_emails_only_owner`

**Qualification:** Automated equivalent using isolated synthetic fixtures; literal manual example accounts and counts were not separately executed.

## UT_34_3  Configured origin controls the login link

**Module:** BL 34 Credential delivery

**Preconditions:** Admin is fully authenticated. Use an isolated database and locally captured email.

**Parameters:**  Fictional owner address; temporary password; configured HTTPS SITE_URL; transport failures where stated.

**Steps:** 1: Prepare the stated recipient/configuration. 2: Trigger the described create/reset/resend operation. 3: Inspect recipients, account state, response and audit without exposing real credentials.

**Expected result:** A forged Host header does not alter the credential link.

**Actual result:** Fresh execution: 1 mapped test method(s) passed. Assertions cover the automated equivalent described by the named methods; this is not a claim of a separate literal manual execution.

**Result:** PASS automated equivalent

**Evidence:** `evidence/part3-2026-11-06/regression.json` (archived)

**Exact test methods:**

- `apps.accounts.test_credential_email.CredentialEmailTests.test_email_uses_configured_origin_not_request_host`

**Qualification:** Automated equivalent using isolated synthetic fixtures; literal manual example accounts and counts were not separately executed.

## UT_34_4  Delivery failure gives a private one-time fallback

**Module:** BL 34 Credential delivery

**Preconditions:** Admin is fully authenticated. Use an isolated database and locally captured email.

**Parameters:**  Fictional owner address; temporary password; configured HTTPS SITE_URL; transport failures where stated.

**Steps:** 1: Prepare the stated recipient/configuration. 2: Trigger the described create/reset/resend operation. 3: Inspect recipients, account state, response and audit without exposing real credentials.

**Expected result:** The account remains saved; fallback appears only in the original response, not later GETs.

**Actual result:** Fresh execution: 1 mapped test method(s) passed. Assertions cover the automated equivalent described by the named methods; this is not a claim of a separate literal manual execution.

**Result:** PASS automated equivalent

**Evidence:** `evidence/part3-2026-11-06/regression.json` (archived)

**Exact test methods:**

- `apps.accounts.test_credential_email.CredentialEmailTests.test_email_failure_keeps_account_and_shows_password_only_in_original_response`

**Qualification:** Automated equivalent using isolated synthetic fixtures; literal manual example accounts and counts were not separately executed.

## UT_34_5  Unsafe production configuration fails safely

**Module:** BL 34 Credential delivery

**Preconditions:** Admin is fully authenticated. Use an isolated database and locally captured email.

**Parameters:**  Fictional owner address; temporary password; configured HTTPS SITE_URL; transport failures where stated.

**Steps:** 1: Prepare the stated recipient/configuration. 2: Trigger the described create/reset/resend operation. 3: Inspect recipients, account state, response and audit without exposing real credentials.

**Expected result:** Unsafe delivery configuration does not expose or misdirect a password.

**Actual result:** Fresh execution: 2 mapped test method(s) passed. Assertions cover the automated equivalent described by the named methods; this is not a claim of a separate literal manual execution.

**Result:** PASS automated equivalent

**Evidence:** `evidence/part3-2026-11-06/regression.json` (archived)

**Exact test methods:**

- `apps.accounts.test_credential_email.CredentialEmailTests.test_production_console_and_file_storage_are_refused`
- `apps.accounts.test_credential_email.CredentialEmailTests.test_invalid_or_non_https_production_origin_falls_back`

**Qualification:** Automated equivalent using isolated synthetic fixtures; literal manual example accounts and counts were not separately executed.

## UT_34_6  Zero sent messages is a delivery failure

**Module:** BL 34 Credential delivery

**Preconditions:** Admin is fully authenticated. Use an isolated database and locally captured email.

**Parameters:**  Fictional owner address; temporary password; configured HTTPS SITE_URL; transport failures where stated.

**Steps:** 1: Prepare the stated recipient/configuration. 2: Trigger the described create/reset/resend operation. 3: Inspect recipients, account state, response and audit without exposing real credentials.

**Expected result:** No false delivery success; reset fallback is available safely.

**Actual result:** Fresh execution: 1 mapped test method(s) passed. Assertions cover the automated equivalent described by the named methods; this is not a claim of a separate literal manual execution.

**Result:** PASS automated equivalent

**Evidence:** `evidence/part3-2026-11-06/regression.json` (archived)

**Exact test methods:**

- `apps.accounts.test_credential_email.CredentialEmailTests.test_zero_messages_sent_is_failure_and_returns_fallback_on_reset`

**Qualification:** Automated equivalent using isolated synthetic fixtures; literal manual example accounts and counts were not separately executed.

## IT_34_1  Profile rollback emits no credential email

**Module:** BL 34 Credential delivery

**Preconditions:** Admin is fully authenticated. Use an isolated database and locally captured email.

**Parameters:**  Fictional owner address; temporary password; configured HTTPS SITE_URL; transport failures where stated.

**Steps:** 1: Prepare the stated recipient/configuration. 2: Trigger the described create/reset/resend operation. 3: Inspect recipients, account state, response and audit without exposing real credentials.

**Expected result:** Failed profile creation rolls back account creation and sends no email.

**Actual result:** Fresh execution: 1 mapped test method(s) passed. Assertions cover the automated equivalent described by the named methods; this is not a claim of a separate literal manual execution.

**Result:** PASS automated equivalent

**Evidence:** `evidence/part3-2026-11-06/regression.json` (archived)

**Exact test methods:**

- `apps.accounts.test_credential_email.CredentialEmailTests.test_failed_profile_transaction_never_sends_email`

**Qualification:** Automated equivalent using isolated synthetic fixtures; literal manual example accounts and counts were not separately executed.

## IT_34_2  Invalid and repeated submissions send no extra credentials

**Module:** BL 34 Credential delivery

**Preconditions:** Admin is fully authenticated. Use an isolated database and locally captured email.

**Parameters:**  Fictional owner address; temporary password; configured HTTPS SITE_URL; transport failures where stated.

**Steps:** 1: Prepare the stated recipient/configuration. 2: Trigger the described create/reset/resend operation. 3: Inspect recipients, account state, response and audit without exposing real credentials.

**Expected result:** No extra mail is sent for rejected submissions.

**Actual result:** Fresh execution: 1 mapped test method(s) passed. Assertions cover the automated equivalent described by the named methods; this is not a claim of a separate literal manual execution.

**Result:** PASS automated equivalent

**Evidence:** `evidence/part3-2026-11-06/regression.json` (archived)

**Exact test methods:**

- `apps.accounts.test_credential_email.CredentialEmailTests.test_invalid_and_duplicate_submissions_do_not_email`

**Qualification:** Automated equivalent using isolated synthetic fixtures; literal manual example accounts and counts were not separately executed.

## IT_34_3  Reset and resend rotate the password

**Module:** BL 34 Credential delivery

**Preconditions:** Admin is fully authenticated. Use an isolated database and locally captured email.

**Parameters:**  Fictional owner address; temporary password; configured HTTPS SITE_URL; transport failures where stated.

**Steps:** 1: Prepare the stated recipient/configuration. 2: Trigger the described create/reset/resend operation. 3: Inspect recipients, account state, response and audit without exposing real credentials.

**Expected result:** Only the current password is delivered; purpose is audited without secrets.

**Actual result:** Fresh execution: 2 mapped test method(s) passed. Assertions cover the automated equivalent described by the named methods; this is not a claim of a separate literal manual execution.

**Result:** PASS automated equivalent

**Evidence:** `evidence/part3-2026-11-06/regression.json` (archived)

**Exact test methods:**

- `apps.accounts.test_credential_email.CredentialEmailTests.test_reset_and_resend_rotate_password_and_audit_purpose`
- `apps.accounts.test_credential_email.CredentialEmailTests.test_stale_password_is_not_sent_or_shown`

**Qualification:** Automated equivalent using isolated synthetic fixtures; literal manual example accounts and counts were not separately executed.

## ST_34_1  Provisioned owner completes secure first login

**Module:** BL 34 Credential delivery

**Preconditions:** Admin is fully authenticated. Use an isolated database and locally captured email.

**Parameters:**  Fictional owner address; temporary password; configured HTTPS SITE_URL; transport failures where stated.

**Steps:** 1: Prepare the stated recipient/configuration. 2: Trigger the described create/reset/resend operation. 3: Inspect recipients, account state, response and audit without exposing real credentials.

**Expected result:** Delivered temporary credentials lead through OTP setup and forced password change.

**Actual result:** Fresh execution: 1 mapped test method(s) passed. Assertions cover the automated equivalent described by the named methods; this is not a claim of a separate literal manual execution.

**Result:** PASS automated equivalent

**Evidence:** `evidence/part3-2026-11-06/regression.json` (archived)

**Exact test methods:**

- `tests.test_integration.ProvisionedAttendanceJourneyTests.test_provisioned_accounts_complete_otp_then_corrected_totals_agree_everywhere`

**Qualification:** Automated equivalent using isolated synthetic fixtures; literal manual example accounts and counts were not separately executed.

## ST_34_2  Only Admin can trigger credential delivery

**Module:** BL 34 Credential delivery

**Preconditions:** Admin is fully authenticated. Use an isolated database and locally captured email.

**Parameters:**  Fictional owner address; temporary password; configured HTTPS SITE_URL; transport failures where stated.

**Steps:** 1: Prepare the stated recipient/configuration. 2: Trigger the described create/reset/resend operation. 3: Inspect recipients, account state, response and audit without exposing real credentials.

**Expected result:** Faculty and Student actions are denied and do not send credentials.

**Actual result:** Fresh execution: 1 mapped test method(s) passed. Assertions cover the automated equivalent described by the named methods; this is not a claim of a separate literal manual execution.

**Result:** PASS automated equivalent

**Evidence:** `evidence/part3-2026-11-06/regression.json` (archived)

**Exact test methods:**

- `apps.accounts.test_credential_email.CredentialEmailTests.test_non_admins_cannot_trigger_creation_reset_resend_or_delivery_service`

**Qualification:** Automated equivalent using isolated synthetic fixtures; literal manual example accounts and counts were not separately executed.

## ST_34_3  Resend requires POST and CSRF

**Module:** BL 34 Credential delivery

**Preconditions:** Admin is fully authenticated. Use an isolated database and locally captured email.

**Parameters:**  Fictional owner address; temporary password; configured HTTPS SITE_URL; transport failures where stated.

**Steps:** 1: Prepare the stated recipient/configuration. 2: Trigger the described create/reset/resend operation. 3: Inspect recipients, account state, response and audit without exposing real credentials.

**Expected result:** GET or a missing CSRF token cannot resend credentials.

**Actual result:** Fresh execution: 1 mapped test method(s) passed. Assertions cover the automated equivalent described by the named methods; this is not a claim of a separate literal manual execution.

**Result:** PASS automated equivalent

**Evidence:** `evidence/part3-2026-11-06/regression.json` (archived)

**Exact test methods:**

- `apps.accounts.test_credential_email.CredentialEmailTests.test_resend_requires_post_and_csrf`

**Qualification:** Automated equivalent using isolated synthetic fixtures; literal manual example accounts and counts were not separately executed.

## ST_34_4  Resend after first password change is refused

**Module:** BL 34 Credential delivery

**Preconditions:** Admin is fully authenticated. Use an isolated database and locally captured email.

**Parameters:**  Fictional owner address; temporary password; configured HTTPS SITE_URL; transport failures where stated.

**Steps:** 1: Prepare the stated recipient/configuration. 2: Trigger the described create/reset/resend operation. 3: Inspect recipients, account state, response and audit without exposing real credentials.

**Expected result:** An account's chosen password cannot be resent or silently replaced.

**Actual result:** Fresh execution: 1 mapped test method(s) passed. Assertions cover the automated equivalent described by the named methods; this is not a claim of a separate literal manual execution.

**Result:** PASS automated equivalent

**Evidence:** `evidence/part3-2026-11-06/regression.json` (archived)

**Exact test methods:**

- `apps.accounts.test_credential_email.CredentialEmailTests.test_resend_after_password_change_is_rejected_without_reset`

**Qualification:** Automated equivalent using isolated synthetic fixtures; literal manual example accounts and counts were not separately executed.

## UT_09_4  Initial report view does not run an unfiltered report

**Module:** UC 09 Required report scope

**Preconditions:** Admin/Faculty is fully authenticated.

**Parameters:**  No scope or date parameters.

**Steps:** Open the initial report page without parameters; inspect data, form and download links.

**Expected result:** An unbound filter form appears; no report or download is generated.

**Actual result:** Fresh execution: 1 mapped test method(s) passed. Assertions cover the automated equivalent described by the named methods; this is not a claim of a separate literal manual execution.

**Result:** PASS automated equivalent

**Evidence:** `evidence/part3-2026-11-06/regression.json` (archived)

**Exact test methods:**

- `tests.test_report_scope.ReportScopeTests.test_initial_report_page_shows_form_without_generating_or_offering_downloads`

**Qualification:** Automated equivalent using isolated synthetic fixtures; literal manual example accounts and counts were not separately executed.

## IT_09_4  An explicit section never exposes another teacher's subjects

**Module:** UC 09 Section authorization

**Preconditions:** Two faculty teach different subjects in the same section.

**Parameters:**  Own/shared section; foreign section; both dates.

**Steps:** Generate an explicit section report as each faculty member; then request a foreign section through HTML, CSV and PDF.

**Expected result:** Only authorized assignments are included; foreign section requests return 403.

**Actual result:** Fresh execution: 2 mapped test method(s) passed. Assertions cover the automated equivalent described by the named methods; this is not a claim of a separate literal manual execution.

**Result:** PASS automated equivalent

**Evidence:** `evidence/part3-2026-11-06/regression.json` (archived)

**Exact test methods:**

- `tests.test_report_scope.ReportScopeTests.test_explicit_section_and_all_scope_preserve_teacher_authorization`
- `tests.test_report_scope.ReportScopeTests.test_foreign_section_is_denied_for_html_and_both_exports`

**Qualification:** Automated equivalent using isolated synthetic fixtures; literal manual example accounts and counts were not separately executed.

## UT_09_5  Status filtering preserves the complete percentage denominator

**Module:** UC 09 Report calculations

**Preconditions:** An authorized student has both Present and Absent marks in the requested range.

**Parameters:**  Both statuses; explicit scope and dates.

**Steps:** Generate the report with a status filter and a student filter; compare totals with all saved marks.

**Expected result:** The filter selects matching groups; percentages retain every eligible mark in each group's denominator.

**Actual result:** Fresh execution: 1 mapped test method(s) passed. Assertions cover the automated equivalent described by the named methods; this is not a claim of a separate literal manual execution.

**Result:** PASS automated equivalent

**Evidence:** `evidence/part3-2026-11-06/regression.json` (archived)

**Exact test methods:**

- `tests.test_integration.AttendanceAlertAndReportIntegrationTests.test_status_and_student_report_filters_preserve_the_real_denominator`

**Qualification:** Automated equivalent using isolated synthetic fixtures; literal manual example accounts and counts were not separately executed.

## UT_30_1  Public pages begin with a real doctype

**Module:** BL 30 Browser standards

**Preconditions:** The application is configured for a local test request.

**Parameters:**  Public/login HTML; local Bootstrap assets.

**Steps:** Request public and login pages and inspect the beginning of each response.

**Expected result:** The first document markup is a valid HTML doctype; no literal Markdown fence precedes it.

**Actual result:** Fresh execution: 1 mapped test method(s) passed. Assertions cover the automated equivalent described by the named methods; this is not a claim of a separate literal manual execution.

**Result:** PASS automated equivalent

**Evidence:** `evidence/part3-2026-11-06/regression.json` (archived)

**Exact test methods:**

- `tests.test_document_mode.DocumentModeTests.test_public_and_login_pages_begin_with_a_real_html_doctype`

**Qualification:** Automated equivalent using isolated synthetic fixtures; literal manual example accounts and counts were not separately executed.

## IT_01_6  Forgot-password request

**Module:** Existing Sprint 2 feedback changes

**Preconditions:** An active student and Admin with fictional email addresses exist.

**Parameters:** Synthetic data defined by the linked test method.

**Steps:** Submit the student username on Forgot password; inspect captured mail and the Admin account list/dashboard.

**Expected result:** The request flags the student, emails only Admins, records an audit event and appears in the Admin views.

**Actual result:** Fresh execution: 1 mapped test method(s) passed. Assertions cover the automated equivalent described by the named methods; this is not a claim of a separate literal manual execution.

**Result:** PASS automated equivalent

**Evidence:** `evidence/part3-2026-11-06/regression.json` (archived)

**Exact test methods:**

- `apps.accounts.test_password_reset_request.ForgotPasswordTests.test_request_flags_account_and_emails_admins`

**Qualification:** Added to the catalogue for current-branch behavior. Automated isolated fixture execution.

## UT_01_9  Forgot-password privacy

**Module:** Existing Sprint 2 feedback changes

**Preconditions:** An active student account exists.

**Parameters:** Synthetic data defined by the linked test method.

**Steps:** Submit its username and an unknown username. Compare response status and body.

**Expected result:** Replies are identical; only the existing account causes an Admin email.

**Actual result:** Fresh execution: 1 mapped test method(s) passed. Assertions cover the automated equivalent described by the named methods; this is not a claim of a separate literal manual execution.

**Result:** PASS automated equivalent

**Evidence:** `evidence/part3-2026-11-06/regression.json` (archived)

**Exact test methods:**

- `apps.accounts.test_password_reset_request.ForgotPasswordTests.test_unknown_and_known_usernames_get_the_same_reply`

**Qualification:** Added to the catalogue for current-branch behavior. Automated isolated fixture execution.

## UT_01_10  Forgot-password rate limit

**Module:** Existing Sprint 2 feedback changes

**Preconditions:** Student and Admin accounts exist.

**Parameters:** Synthetic data defined by the linked test method.

**Steps:** Submit two requests for the same student within 15 minutes.

**Expected result:** Only one Admin email is sent.

**Actual result:** Fresh execution: 1 mapped test method(s) passed. Assertions cover the automated equivalent described by the named methods; this is not a claim of a separate literal manual execution.

**Result:** PASS automated equivalent

**Evidence:** `evidence/part3-2026-11-06/regression.json` (archived)

**Exact test methods:**

- `apps.accounts.test_password_reset_request.ForgotPasswordTests.test_repeat_request_within_15_minutes_sends_no_more_email`

**Qualification:** Added to the catalogue for current-branch behavior. Automated isolated fixture execution.

## IT_01_7  Reset request resolution

**Module:** Existing Sprint 2 feedback changes

**Preconditions:** A student has requested a reset.

**Parameters:** Synthetic data defined by the linked test method.

**Steps:** Perform the Admin password reset and reload the student.

**Expected result:** The pending reset request is cleared.

**Actual result:** Fresh execution: 1 mapped test method(s) passed. Assertions cover the automated equivalent described by the named methods; this is not a claim of a separate literal manual execution.

**Result:** PASS automated equivalent

**Evidence:** `evidence/part3-2026-11-06/regression.json` (archived)

**Exact test methods:**

- `apps.accounts.test_password_reset_request.ForgotPasswordTests.test_admin_reset_clears_the_request`

**Qualification:** Added to the catalogue for current-branch behavior. Automated isolated fixture execution.

## UT_01_11  Login warning privacy

**Module:** Existing Sprint 2 feedback changes

**Preconditions:** Use separate client sessions for known and unknown usernames.

**Parameters:** Synthetic data defined by the linked test method.

**Steps:** Submit five wrong passwords per username.

**Expected result:** The fifth failure shows the same 15-minute pause warning for both cases.

**Actual result:** Fresh execution: 1 mapped test method(s) passed. Assertions cover the automated equivalent described by the named methods; this is not a claim of a separate literal manual execution.

**Result:** PASS automated equivalent

**Evidence:** `evidence/part3-2026-11-06/regression.json` (archived)

**Exact test methods:**

- `apps.accounts.test_password_reset_request.LoginLockoutWarningTests.test_fifth_failure_warns_about_the_pause_for_real_and_unknown_accounts`

**Qualification:** Added to the catalogue for current-branch behavior. Automated isolated fixture execution.

## UT_01_12  Login failure counter reset

**Module:** Existing Sprint 2 feedback changes

**Preconditions:** An active account exists.

**Parameters:** Synthetic data defined by the linked test method.

**Steps:** Submit three wrong passwords and then the correct password.

**Expected result:** A successful password submission clears the browser failure counter.

**Actual result:** Fresh execution: 1 mapped test method(s) passed. Assertions cover the automated equivalent described by the named methods; this is not a claim of a separate literal manual execution.

**Result:** PASS automated equivalent

**Evidence:** `evidence/part3-2026-11-06/regression.json` (archived)

**Exact test methods:**

- `apps.accounts.test_password_reset_request.LoginLockoutWarningTests.test_successful_login_clears_the_counter`

**Qualification:** Added to the catalogue for current-branch behavior. Automated isolated fixture execution.

## ST_02_7  Student profile

**Module:** Existing Sprint 2 feedback changes

**Preconditions:** A student is enrolled in a teaching assignment.

**Parameters:** Synthetic data defined by the linked test method.

**Steps:** Open My profile as the student.

**Expected result:** The profile shows the student roll number, enrolled subject and assigned teacher.

**Actual result:** Fresh execution: 1 mapped test method(s) passed. Assertions cover the automated equivalent described by the named methods; this is not a claim of a separate literal manual execution.

**Result:** PASS automated equivalent

**Evidence:** `evidence/part3-2026-11-06/regression.json` (archived)

**Exact test methods:**

- `apps.accounts.test_profile.MyProfileTests.test_student_sees_roll_number_subjects_and_teacher`

**Qualification:** Added to the catalogue for current-branch behavior. Automated isolated fixture execution.

## ST_03_6  Faculty profile scope

**Module:** Existing Sprint 2 feedback changes

**Preconditions:** Two faculty teach different subjects in a shared section.

**Parameters:** Synthetic data defined by the linked test method.

**Steps:** Open My profile as the first faculty member.

**Expected result:** The faculty details and assigned subject are shown; the other faculty subject is absent.

**Actual result:** Fresh execution: 1 mapped test method(s) passed. Assertions cover the automated equivalent described by the named methods; this is not a claim of a separate literal manual execution.

**Result:** PASS automated equivalent

**Evidence:** `evidence/part3-2026-11-06/regression.json` (archived)

**Exact test methods:**

- `apps.accounts.test_profile.MyProfileTests.test_faculty_see_their_details_and_only_their_classes`

**Qualification:** Added to the catalogue for current-branch behavior. Automated isolated fixture execution.

## ST_12_4  Admin profile

**Module:** Existing Sprint 2 feedback changes

**Preconditions:** An Admin account exists.

**Parameters:** Synthetic data defined by the linked test method.

**Steps:** Open My profile as the Admin.

**Expected result:** Account email, Admin access and Change password navigation are visible.

**Actual result:** Fresh execution: 1 mapped test method(s) passed. Assertions cover the automated equivalent described by the named methods; this is not a claim of a separate literal manual execution.

**Result:** PASS automated equivalent

**Evidence:** `evidence/part3-2026-11-06/regression.json` (archived)

**Exact test methods:**

- `apps.accounts.test_profile.MyProfileTests.test_admin_sees_account_details_and_change_password`

**Qualification:** Added to the catalogue for current-branch behavior. Automated isolated fixture execution.

## UT_12_4  Profile access guard

**Module:** Existing Sprint 2 feedback changes

**Preconditions:** No active login session.

**Parameters:** Synthetic data defined by the linked test method.

**Steps:** Request My profile.

**Expected result:** The response redirects to login.

**Actual result:** Fresh execution: 1 mapped test method(s) passed. Assertions cover the automated equivalent described by the named methods; this is not a claim of a separate literal manual execution.

**Result:** PASS automated equivalent

**Evidence:** `evidence/part3-2026-11-06/regression.json` (archived)

**Exact test methods:**

- `apps.accounts.test_profile.MyProfileTests.test_anonymous_users_must_log_in`

**Qualification:** Added to the catalogue for current-branch behavior. Automated isolated fixture execution.

## IT_12_4  Profile navigation

**Module:** Existing Sprint 2 feedback changes

**Preconditions:** Admin is signed in.

**Parameters:** Synthetic data defined by the linked test method.

**Steps:** Open the dashboard and inspect the profile navigation link.

**Expected result:** The navigation contains the My profile route.

**Actual result:** Fresh execution: 1 mapped test method(s) passed. Assertions cover the automated equivalent described by the named methods; this is not a claim of a separate literal manual execution.

**Result:** PASS automated equivalent

**Evidence:** `evidence/part3-2026-11-06/regression.json` (archived)

**Exact test methods:**

- `apps.accounts.test_profile.MyProfileTests.test_navbar_name_links_to_profile`

**Qualification:** Added to the catalogue for current-branch behavior. Automated isolated fixture execution.

## UT_05_4  Optional section batch year

**Module:** Existing Sprint 2 feedback changes

**Preconditions:** Admin is signed in.

**Parameters:** Synthetic data defined by the linked test method.

**Steps:** Create a section with year 2028 and inspect its label; exercise duplicate handling with and without a year.

**Expected result:** Year is included in the section identity; duplicates with the same identity are rejected and an omitted year is supported.

**Actual result:** Fresh execution: 1 mapped test method(s) passed. Assertions cover the automated equivalent described by the named methods; this is not a claim of a separate literal manual execution.

**Result:** PASS automated equivalent

**Evidence:** `evidence/part3-2026-11-06/regression.json` (archived)

**Exact test methods:**

- `apps.academics.test_section_enrollment.SectionEnrollmentTests.test_section_year_is_optional_and_part_of_the_name`

**Qualification:** Added to the catalogue for current-branch behavior. Automated isolated fixture execution.

## IT_05_4  Edit section batch year

**Module:** Existing Sprint 2 feedback changes

**Preconditions:** Admin and an existing section.

**Parameters:** Synthetic data defined by the linked test method.

**Steps:** Edit its year and reload the section.

**Expected result:** The saved year is updated and the edit is audited.

**Actual result:** Fresh execution: 1 mapped test method(s) passed. Assertions cover the automated equivalent described by the named methods; this is not a claim of a separate literal manual execution.

**Result:** PASS automated equivalent

**Evidence:** `evidence/part3-2026-11-06/regression.json` (archived)

**Exact test methods:**

- `apps.academics.test_section_enrollment.SectionEnrollmentTests.test_admin_edits_section_year`

**Qualification:** Added to the catalogue for current-branch behavior. Automated isolated fixture execution.

## ST_05_3  Safe section deletion

**Module:** Existing Sprint 2 feedback changes

**Preconditions:** Admin, an unused section and a section with dependencies.

**Parameters:** Synthetic data defined by the linked test method.

**Steps:** Delete the unused section; attempt to delete the used section.

**Expected result:** The unused section is removed; the used section and its references remain.

**Actual result:** Fresh execution: 1 mapped test method(s) passed. Assertions cover the automated equivalent described by the named methods; this is not a claim of a separate literal manual execution.

**Result:** PASS automated equivalent

**Evidence:** `evidence/part3-2026-11-06/regression.json` (archived)

**Exact test methods:**

- `apps.academics.test_section_enrollment.SectionEnrollmentTests.test_unused_section_can_be_deleted_but_used_one_is_kept`

**Qualification:** Added to the catalogue for current-branch behavior. Automated isolated fixture execution.

## IT_05_5  Section mutation authorization

**Module:** Existing Sprint 2 feedback changes

**Preconditions:** Faculty account and a section.

**Parameters:** Synthetic data defined by the linked test method.

**Steps:** Attempt section edit and deletion as Faculty.

**Expected result:** Both operations are denied and the section remains unchanged.

**Actual result:** Fresh execution: 1 mapped test method(s) passed. Assertions cover the automated equivalent described by the named methods; this is not a claim of a separate literal manual execution.

**Result:** PASS automated equivalent

**Evidence:** `evidence/part3-2026-11-06/regression.json` (archived)

**Exact test methods:**

- `apps.academics.test_section_enrollment.SectionEnrollmentTests.test_faculty_cannot_edit_or_delete_sections`

**Qualification:** Added to the catalogue for current-branch behavior. Automated isolated fixture execution.

## IT_05_6  Student list subject scope

**Module:** Existing Sprint 2 feedback changes

**Preconditions:** Two teachers share students across different subjects.

**Parameters:** Synthetic data defined by the linked test method.

**Steps:** Open the student list as one teacher.

**Expected result:** Only subjects taught by that teacher are shown for each student.

**Actual result:** Fresh execution: 1 mapped test method(s) passed. Assertions cover the automated equivalent described by the named methods; this is not a claim of a separate literal manual execution.

**Result:** PASS automated equivalent

**Evidence:** `evidence/part3-2026-11-06/regression.json` (archived)

**Exact test methods:**

- `apps.academics.test_section_enrollment.StudentListSubjectsTests.test_faculty_see_only_subjects_they_teach_each_student`

**Qualification:** Added to the catalogue for current-branch behavior. Automated isolated fixture execution.

## UT_01_13  Forgot-password navigation

**Module:** Existing Sprint 2 feedback changes

**Preconditions:** An authenticated student session exists.

**Parameters:** Synthetic data defined by the linked test method.

**Steps:** Request Forgot password while authenticated.

**Expected result:** The student is redirected to the dashboard.

**Actual result:** Fresh execution: 1 mapped test method(s) passed. Assertions cover the automated equivalent described by the named methods; this is not a claim of a separate literal manual execution.

**Result:** PASS automated equivalent

**Evidence:** `evidence/part3-2026-11-06/regression.json` (archived)

**Exact test methods:**

- `apps.accounts.test_password_reset_request.ForgotPasswordTests.test_signed_in_users_are_sent_to_their_dashboard`

**Qualification:** Added to the catalogue for current-branch behavior. Automated isolated fixture execution.

## UT_01_14  Two-factor pages opened out of order or while locked

**Module:** Authentication / BL-33

**Preconditions:** Student account with and without a confirmed authenticator.

**Parameters:** Synthetic data defined by the linked test method.

**Steps:** Open code entry and request an email code before setup; open them again after verification; lock the account after the password step and open code entry.

**Expected result:** Users without an authenticator are sent to setup; verified users skip the code pages; a lock that starts after the password signs the user out.

**Actual result:** Fresh execution: 3 mapped test method(s) passed. Assertions cover the automated equivalent described by the named methods; this is not a claim of a separate literal manual execution.

**Result:** PASS automated equivalent

**Evidence:** `artifacts/part3/rerun-2026-11-06/regression.json` (local rerun, 6 November 2026)

**Exact test methods:**

- `apps.accounts.test_otp_error_paths.OTPPageOrderTests.test_code_pages_send_users_without_an_authenticator_to_setup`
- `apps.accounts.test_otp_error_paths.OTPPageOrderTests.test_already_verified_users_skip_the_code_pages`
- `apps.accounts.test_otp_error_paths.OTPPageOrderTests.test_a_lock_that_starts_after_the_password_signs_the_user_out`

**Qualification:** Added in the Part 3 coverage follow-up. Automated isolated fixture execution; no application code was changed.

## IT_01_8  Account changes during authenticator setup

**Module:** Authentication / BL-33

**Preconditions:** Student has opened the authenticator setup page.

**Parameters:** Synthetic data defined by the linked test method.

**Steps:** Submit the first code while the account becomes locked; submit it after setup was finished in another tab.

**Expected result:** A lock signs the user out; a setup finished elsewhere sends the user to code entry and discards the unused setup secret.

**Actual result:** Fresh execution: 2 mapped test method(s) passed. Assertions cover the automated equivalent described by the named methods; this is not a claim of a separate literal manual execution.

**Result:** PASS automated equivalent

**Evidence:** `artifacts/part3/rerun-2026-11-06/regression.json` (local rerun, 6 November 2026)

**Exact test methods:**

- `apps.accounts.test_otp_error_paths.OTPSetupRaceTests.test_lock_during_setup_signs_the_user_out`
- `apps.accounts.test_otp_error_paths.OTPSetupRaceTests.test_setup_finished_in_another_tab_goes_to_code_entry`

**Qualification:** Added in the Part 3 coverage follow-up. Automated isolated fixture execution; no application code was changed. The concurrent change is simulated by making the setup service report it.

## UT_02_4  Whitespace-only names are rejected by the form clean methods

**Module:** Student, Faculty, Course and Class Management / BL-07 to BL-10

**Preconditions:** None.

**Parameters:** Synthetic data defined by the linked test method.

**Steps:** Call each name clean method with a value made only of spaces: student name, Dept and sem, Section, subject name, faculty name and department.

**Expected result:** Each method rejects the value with its field-specific required message.

**Actual result:** Fresh execution: 1 mapped test method(s) passed. Assertions cover the automated equivalent described by the named methods; this is not a claim of a separate literal manual execution.

**Result:** PASS automated equivalent

**Evidence:** `artifacts/part3/rerun-2026-11-06/regression.json` (local rerun, 6 November 2026)

**Exact test methods:**

- `apps.academics.test_error_paths.BlankFieldGuardTests.test_whitespace_only_values_are_rejected_by_each_clean_method`

**Qualification:** Added in the Part 3 coverage follow-up. Automated isolated fixture execution; no application code was changed. Through the web page Django rejects blank input before these methods run, so the methods are tested directly as the backup guard.

## UT_02_5  Unsupported characters in login identifiers

**Module:** Student Management / BL-07; Faculty Management / BL-08

**Preconditions:** A section exists.

**Parameters:** Synthetic data defined by the linked test method.

**Steps:** Submit a roll number containing # and a faculty ID containing a space.

**Expected result:** Both forms are invalid with 'Use letters, numbers or @ . + - _ only.'

**Actual result:** Fresh execution: 2 mapped test method(s) passed. Assertions cover the automated equivalent described by the named methods; this is not a claim of a separate literal manual execution.

**Result:** PASS automated equivalent

**Evidence:** `artifacts/part3/rerun-2026-11-06/regression.json` (local rerun, 6 November 2026)

**Exact test methods:**

- `apps.academics.test_error_paths.LoginIdentifierFormatTests.test_roll_number_with_unsupported_characters_is_rejected`
- `apps.academics.test_error_paths.LoginIdentifierFormatTests.test_faculty_id_with_unsupported_characters_is_rejected`

**Qualification:** Added in the Part 3 coverage follow-up. Automated isolated fixture execution; no application code was changed.

## ST_02_8  Invalid edits and repeated Admin actions change nothing

**Module:** Student, Faculty, Course and Class Management / BL-07 to BL-10

**Preconditions:** Admin is signed in; a student, faculty member, section and subject exist.

**Parameters:** Synthetic data defined by the linked test method.

**Steps:** Submit invalid student, section, subject and faculty edits; repeat a deactivate or reactivate that is already in effect; open the student delete page.

**Expected result:** Invalid edits re-display the form and save nothing; repeated actions add no audit entries; the delete page asks for confirmation and deletes nothing.

**Actual result:** Fresh execution: 3 mapped test method(s) passed. Assertions cover the automated equivalent described by the named methods; this is not a claim of a separate literal manual execution.

**Result:** PASS automated equivalent

**Evidence:** `artifacts/part3/rerun-2026-11-06/regression.json` (local rerun, 6 November 2026)

**Exact test methods:**

- `apps.academics.test_error_paths.AdminViewErrorPathTests.test_invalid_edit_forms_show_the_page_again_and_change_nothing`
- `apps.academics.test_error_paths.AdminViewErrorPathTests.test_repeating_deactivate_or_reactivate_changes_nothing_and_is_not_logged_again`
- `apps.academics.test_error_paths.AdminViewErrorPathTests.test_student_delete_page_asks_for_confirmation_before_deleting`

**Qualification:** Added in the Part 3 coverage follow-up. Automated isolated fixture execution; no application code was changed.

## IT_05_7  Duplicates saved concurrently by another Admin

**Module:** Class Management / BL-10, BL-11; Course Management / BL-09

**Preconditions:** Admin is signed in; a section, subjects, a student and a faculty member exist.

**Parameters:** Synthetic data defined by the linked test method.

**Steps:** Create or edit a section, enroll a student, create a subject, offer a subject and assign a class while the database refuses the save as a duplicate.

**Expected result:** Each page shows its duplicate message, nothing is saved and no audit entry is written.

**Actual result:** Fresh execution: 4 mapped test method(s) passed. Assertions cover the automated equivalent described by the named methods; this is not a claim of a separate literal manual execution.

**Result:** PASS automated equivalent

**Evidence:** `artifacts/part3/rerun-2026-11-06/regression.json` (local rerun, 6 November 2026)

**Exact test methods:**

- `apps.academics.test_error_paths.ConcurrentDuplicateTests.test_section_create_and_edit_report_a_duplicate_saved_meanwhile`
- `apps.academics.test_error_paths.ConcurrentDuplicateTests.test_enrollment_reports_a_conflict_saved_meanwhile`
- `apps.academics.test_error_paths.ConcurrentDuplicateTests.test_subject_create_reports_a_code_saved_meanwhile`
- `apps.academics.test_error_paths.ConcurrentDuplicateTests.test_subject_offer_and_class_assign_report_an_offering_saved_meanwhile`

**Qualification:** Added in the Part 3 coverage follow-up. Automated isolated fixture execution; no application code was changed. The concurrent duplicate is simulated by making the save raise the database's integrity error.

## UT_06_7  Marking service guards

**Module:** Attendance Marking / BL-12, BL-13

**Preconditions:** Faculty member assigned to a class.

**Parameters:** Synthetic data defined by the linked test method.

**Steps:** Call the marking service as a signed-out user and as a deleted account; with a future date; with a non-text reason; for a class with no active students.

**Expected result:** Each call is refused with the matching permission or validation message and no session is created.

**Actual result:** Fresh execution: 4 mapped test method(s) passed. Assertions cover the automated equivalent described by the named methods; this is not a claim of a separate literal manual execution.

**Result:** PASS automated equivalent

**Evidence:** `artifacts/part3/rerun-2026-11-06/regression.json` (local rerun, 6 November 2026)

**Exact test methods:**

- `apps.attendance.test_error_paths.AttendanceGuardTests.test_marking_requires_a_signed_in_account_that_still_exists`
- `apps.attendance.test_error_paths.AttendanceGuardTests.test_marking_refuses_a_future_date_even_without_the_date_picker`
- `apps.attendance.test_error_paths.AttendanceGuardTests.test_marking_reason_must_be_text`
- `apps.attendance.test_error_paths.AttendanceGuardTests.test_marking_a_class_with_no_active_students_is_refused`

**Qualification:** Added in the Part 3 coverage follow-up. Automated isolated fixture execution; no application code was changed.

## UT_07_6  Correction service guards

**Module:** Attendance Correction / BL-17, BL-18

**Preconditions:** Faculty member, Admin and one saved Absent mark.

**Parameters:** Synthetic data defined by the linked test method.

**Steps:** Correct as a signed-out user; correct a record that no longer exists; change the correction window with a non-text reason.

**Expected result:** Each call is refused; the saved mark stays Absent and the window stays at 2 days.

**Actual result:** Fresh execution: 2 mapped test method(s) passed. Assertions cover the automated equivalent described by the named methods; this is not a claim of a separate literal manual execution.

**Result:** PASS automated equivalent

**Evidence:** `artifacts/part3/rerun-2026-11-06/regression.json` (local rerun, 6 November 2026)

**Exact test methods:**

- `apps.attendance.test_error_paths.AttendanceGuardTests.test_correction_requires_a_signed_in_account_and_an_existing_record`
- `apps.attendance.test_error_paths.AttendanceGuardTests.test_correction_window_reason_must_be_text`

**Qualification:** Added in the Part 3 coverage follow-up. Automated isolated fixture execution; no application code was changed.

## ST_07_6  Correction window page errors

**Module:** Attendance Correction / BL-17, BL-18

**Preconditions:** Admin is signed in.

**Parameters:** Synthetic data defined by the linked test method.

**Steps:** Save the current window value again; save a new value while the database fails.

**Expected result:** The page explains that nothing changed, or that the change could not be saved; the failure is logged and the window is unchanged.

**Actual result:** Fresh execution: 2 mapped test method(s) passed. Assertions cover the automated equivalent described by the named methods; this is not a claim of a separate literal manual execution.

**Result:** PASS automated equivalent

**Evidence:** `artifacts/part3/rerun-2026-11-06/regression.json` (local rerun, 6 November 2026)

**Exact test methods:**

- `apps.attendance.test_error_paths.CorrectionWindowPageErrorTests.test_saving_the_current_value_explains_that_nothing_changed`
- `apps.attendance.test_error_paths.CorrectionWindowPageErrorTests.test_a_database_failure_is_reported_and_logged_without_saving`

**Qualification:** Added in the Part 3 coverage follow-up. Automated isolated fixture execution; no application code was changed. The database failure is simulated.

## UT_13_4  Damaged or tampered backup snapshots are rejected

**Module:** Backup & Recovery / BL-26, BL-27

**Preconditions:** An active Admin exists and a snapshot is captured from the test database.

**Parameters:** Synthetic data defined by the linked test method.

**Steps:** Validate the captured snapshot; then validate copies that are not an object, have a naive or missing time, a missing table, a table that is not a list, an extra column, a duplicate ID, or no active Admin.

**Expected result:** The captured snapshot is accepted; every damaged copy is rejected with the safe corrupt/incompatible message or the active-Admin message.

**Actual result:** Fresh execution: 4 mapped test method(s) passed. Assertions cover the automated equivalent described by the named methods; this is not a claim of a separate literal manual execution.

**Result:** PASS automated equivalent

**Evidence:** `artifacts/part3/rerun-2026-11-06/regression.json` (local rerun, 6 November 2026)

**Exact test methods:**

- `apps.backups.test_error_paths.SnapshotValidationTests.test_captured_snapshot_is_valid`
- `apps.backups.test_error_paths.SnapshotValidationTests.test_a_payload_that_is_not_an_object_is_rejected`
- `apps.backups.test_error_paths.SnapshotValidationTests.test_damaged_structures_are_rejected`
- `apps.backups.test_error_paths.SnapshotValidationTests.test_a_snapshot_without_an_active_admin_is_rejected`

**Qualification:** Added in the Part 3 coverage follow-up. Automated isolated fixture execution; no application code was changed.

## UT_13_5  Scheduled-backup command when busy or failing

**Module:** Backup & Recovery / BL-26

**Preconditions:** None.

**Parameters:** Synthetic data defined by the linked test method.

**Steps:** Run the scheduler command while another backup operation is active; run it when the backup fails.

**Expected result:** A busy tick prints that it will retry next minute; a failure exits with the safe error message.

**Actual result:** Fresh execution: 2 mapped test method(s) passed. Assertions cover the automated equivalent described by the named methods; this is not a claim of a separate literal manual execution.

**Result:** PASS automated equivalent

**Evidence:** `artifacts/part3/rerun-2026-11-06/regression.json` (local rerun, 6 November 2026)

**Exact test methods:**

- `apps.backups.test_error_paths.SchedulerCommandErrorTests.test_busy_tick_waits_for_the_next_minute`
- `apps.backups.test_error_paths.SchedulerCommandErrorTests.test_backup_failure_exits_with_the_safe_message`

**Qualification:** Added in the Part 3 coverage follow-up. Automated isolated fixture execution; no application code was changed. The busy and failed states are simulated.

## UT_12_5  Server entry points load

**Module:** Deployment / NFR-09

**Preconditions:** None.

**Parameters:** Synthetic data defined by the linked test method.

**Steps:** Import the WSGI and ASGI modules a production web server loads.

**Expected result:** Both expose a callable application.

**Actual result:** Fresh execution: 1 mapped test method(s) passed. Assertions cover the automated equivalent described by the named methods; this is not a claim of a separate literal manual execution.

**Result:** PASS automated equivalent

**Evidence:** `artifacts/part3/rerun-2026-11-06/regression.json` (local rerun, 6 November 2026)

**Exact test methods:**

- `config.test_entrypoints.ServerEntryPointTests.test_wsgi_and_asgi_modules_expose_a_callable_application`

**Qualification:** Added in the Part 3 coverage follow-up. Automated isolated fixture execution; no application code was changed.

## UT_01_15  Verify Send emails the username and current temporary password and saves the address.

**Module:** Account Provisioning / FR-24

**Preconditions:** Admin has just reset F002, who has no email address.

**Parameters:**  F002; f002@example.edu.

**Steps:** 1: Reset F002's password. 2: Enter f002@example.edu under Send these details by email. 3: Select Send.

**Expected result:** The email reaches the address with username, temporary password and login link; the page confirms sending and no longer shows the password; the address is saved on F002 and the change is logged (masked).

**Actual result:** Fresh execution on 9 November 2026: 1 mapped test method(s) passed. Assertions cover the automated equivalent described by the named methods; this is not a claim of a separate literal manual execution.

**Result:** PASS automated equivalent

**Evidence:** `artifacts/part3/rerun-2026-11-09/regression.json` (local)

**Exact test methods:**

- `apps.accounts.test_send_credentials.SendCredentialsTests.test_send_emails_the_details_and_saves_the_address`

**Qualification:** Automated equivalent using isolated synthetic fixtures; added with the 9 November 2026 changes (BL-01 D-24 to D-28).

## UT_01_16  Verify only the current temporary password can be sent.

**Module:** Account Provisioning / FR-24

**Preconditions:** F002 has a temporary password.

**Parameters:**  Password value Not#TheRealOne1.

**Steps:** 1: Post the Send form with a different password value. 2: Check the outbox.

**Expected result:** The request is refused and the Admin returns to Accounts; nothing is emailed and the address is not saved.

**Actual result:** Fresh execution on 9 November 2026: 1 mapped test method(s) passed. Assertions cover the automated equivalent described by the named methods; this is not a claim of a separate literal manual execution.

**Result:** PASS automated equivalent

**Evidence:** `artifacts/part3/rerun-2026-11-09/regression.json` (local)

**Exact test methods:**

- `apps.accounts.test_send_credentials.SendCredentialsTests.test_only_the_current_temporary_password_can_be_sent`

**Qualification:** Automated equivalent using isolated synthetic fixtures; added with the 9 November 2026 changes (BL-01 D-24 to D-28).

## UT_01_17  Verify an invalid address shows the form again and sends nothing.

**Module:** Account Provisioning / FR-24

**Preconditions:** F002 has a temporary password.

**Parameters:**  not-an-email.

**Steps:** 1: Enter not-an-email. 2: Select Send.

**Expected result:** "Enter a valid email address." is shown with the password still visible; nothing is emailed.

**Actual result:** Fresh execution on 9 November 2026: 1 mapped test method(s) passed. Assertions cover the automated equivalent described by the named methods; this is not a claim of a separate literal manual execution.

**Result:** PASS automated equivalent

**Evidence:** `artifacts/part3/rerun-2026-11-09/regression.json` (local)

**Exact test methods:**

- `apps.accounts.test_send_credentials.SendCredentialsTests.test_an_invalid_address_shows_the_form_again`

**Qualification:** Automated equivalent using isolated synthetic fixtures; added with the 9 November 2026 changes (BL-01 D-24 to D-28).

## IT_01_9  Verify only the Admin can send login details.

**Module:** Account Provisioning / FR-24, SEC-14

**Preconditions:** A faculty member is logged in.

**Parameters:**  F003 session.

**Steps:** 1: Post the Send form for F002 as the faculty member.

**Expected result:** The server returns 403 and nothing is emailed.

**Actual result:** Fresh execution on 9 November 2026: 1 mapped test method(s) passed. Assertions cover the automated equivalent described by the named methods; this is not a claim of a separate literal manual execution.

**Result:** PASS automated equivalent

**Evidence:** `artifacts/part3/rerun-2026-11-09/regression.json` (local)

**Exact test methods:**

- `apps.accounts.test_send_credentials.SendCredentialsTests.test_only_the_admin_can_send_login_details`

**Qualification:** Automated equivalent using isolated synthetic fixtures; added with the 9 November 2026 changes (BL-01 D-24 to D-28).

## IT_11_4  Verify records are listed only after the filters are applied.

**Module:** Attendance History / FR-10, D-27

**Preconditions:** Faculty member with recorded sessions.

**Parameters:**  Faculty F001.

**Steps:** 1: Open Attendance history. 2: Check the results area. 3: Select Apply filters with no filters chosen.

**Expected result:** Before applying, the page asks the user to apply filters and lists no records; after applying, every record in the faculty member's scope is listed.

**Actual result:** Fresh execution on 9 November 2026: 1 mapped test method(s) passed. Assertions cover the automated equivalent described by the named methods; this is not a claim of a separate literal manual execution.

**Result:** PASS automated equivalent

**Evidence:** `artifacts/part3/rerun-2026-11-09/regression.json` (local)

**Exact test methods:**

- `apps.attendance.test_history.AttendanceHistoryTests.test_records_appear_only_after_the_filters_are_applied`

**Qualification:** Automated equivalent using isolated synthetic fixtures; added with the 9 November 2026 changes (BL-01 D-24 to D-28).

## IT_12_5  Verify dashboard shortage counts exclude deactivated students and match the list.

**Module:** Dashboard / FR-17, D-28

**Preconditions:** Only below-threshold student is deactivated.

**Parameters:**  S001 at 1/3 (33.33%), threshold 75%.

**Steps:** 1: Deactivate the student. 2: Open the Faculty dashboard. 3: Open Students below threshold.

**Expected result:** The dashboard counts 0 and hides the shortage box; the list shows no students.

**Actual result:** Fresh execution on 9 November 2026: 1 mapped test method(s) passed. Assertions cover the automated equivalent described by the named methods; this is not a claim of a separate literal manual execution.

**Result:** PASS automated equivalent

**Evidence:** `artifacts/part3/rerun-2026-11-09/regression.json` (local)

**Exact test methods:**

- `apps.attendance.test_outlook.TodayOverviewTests.test_dashboard_count_matches_the_list_when_the_student_is_deactivated`

**Qualification:** Automated equivalent using isolated synthetic fixtures; added with the 9 November 2026 changes (BL-01 D-24 to D-28).

## IT_12_6  Verify the sidebar lists only the role's own pages and marks the current page.

**Module:** Navigation / FR-02, FR-17, SEC-10

**Preconditions:** One user of each role.

**Parameters:**  ADMIN1, F001, S001.

**Steps:** 1: Open each role's dashboard. 2: Open every sidebar link. 3: Open Create Admin account as Admin.

**Expected result:** Every listed link opens for its role; students see no staff pages, faculty no Admin settings; exactly one link is marked current (the longest matching path).

**Actual result:** Fresh execution on 9 November 2026: 5 mapped test method(s) passed. Assertions cover the automated equivalent described by the named methods; this is not a claim of a separate literal manual execution.

**Result:** PASS automated equivalent

**Evidence:** `artifacts/part3/rerun-2026-11-09/regression.json` (local)

**Exact test methods:**

- `apps.accounts.test_layout.SidebarTests.test_every_sidebar_link_opens_for_its_role`
- `apps.accounts.test_layout.SidebarTests.test_student_sidebar_has_no_staff_pages`
- `apps.accounts.test_layout.SidebarTests.test_faculty_sidebar_has_no_admin_settings`
- `apps.accounts.test_layout.SidebarTests.test_current_page_is_marked_and_longest_match_wins`
- `apps.accounts.test_layout.SidebarTests.test_sign_in_pages_have_no_sidebar`

**Qualification:** Automated equivalent using isolated synthetic fixtures; added with the 9 November 2026 changes (BL-01 D-24 to D-28).

## UT_14_1  Verify the Admin can add and remove a timetable class, and both are logged.

**Module:** Timetable / FR-22

**Preconditions:** Admin logged in; CS101 offered in section A.

**Parameters:**  Monday, period 1.

**Steps:** 1: Add CS101 – A on Monday period 1. 2: Remove it.

**Expected result:** The class appears under Monday and is then removed; both actions are in the audit log.

**Actual result:** Fresh execution on 9 November 2026: 1 mapped test method(s) passed. Assertions cover the automated equivalent described by the named methods; this is not a claim of a separate literal manual execution.

**Result:** PASS automated equivalent

**Evidence:** `artifacts/part3/rerun-2026-11-09/regression.json` (local)

**Exact test methods:**

- `apps.academics.test_planning.PlanningTests.test_admin_adds_and_removes_timetable_classes`

**Qualification:** Automated equivalent using isolated synthetic fixtures; added with the 9 November 2026 changes (BL-01 D-24 to D-28).

## UT_14_2  Verify a clash for the section or the teacher is rejected.

**Module:** Timetable / FR-22

**Preconditions:** CS101 – A is on Monday period 1.

**Parameters:**  Monday, period 1.

**Steps:** 1: Add MA101 – A on Monday period 1. 2: Add CS101 – B (same teacher) on Monday period 1. 3: Add CS101 – A again.

**Expected result:** Each entry is rejected (400) naming the clash; only the first class remains.

**Actual result:** Fresh execution on 9 November 2026: 1 mapped test method(s) passed. Assertions cover the automated equivalent described by the named methods; this is not a claim of a separate literal manual execution.

**Result:** PASS automated equivalent

**Evidence:** `artifacts/part3/rerun-2026-11-09/regression.json` (local)

**Exact test methods:**

- `apps.academics.test_planning.PlanningTests.test_clashes_for_a_section_or_a_teacher_are_rejected`

**Qualification:** Automated equivalent using isolated synthetic fixtures; added with the 9 November 2026 changes (BL-01 D-24 to D-28).

## UT_14_3  Verify today's classes show marked, now, upcoming and due states and the next class.

**Module:** Timetable / FR-22

**Preconditions:** Periods 1–3 timetabled on Monday; period 1 marked.

**Parameters:**  Monday 9 Nov 2026, IST.

**Steps:** 1: View the overview at 9:30 am. 2: View it at 12:30 pm.

**Expected result:** At 9:30: marked, now, upcoming and next class = period 2. At 12:30: marked, due, due, no next class, 2 not marked.

**Actual result:** Fresh execution on 9 November 2026: 1 mapped test method(s) passed. Assertions cover the automated equivalent described by the named methods; this is not a claim of a separate literal manual execution.

**Result:** PASS automated equivalent

**Evidence:** `artifacts/part3/rerun-2026-11-09/regression.json` (local)

**Exact test methods:**

- `apps.attendance.test_outlook.TodayOverviewTests.test_states_and_next_class_follow_the_clock_and_saved_sessions`

**Qualification:** Automated equivalent using isolated synthetic fixtures; added with the 9 November 2026 changes (BL-01 D-24 to D-28).

## IT_14_1  Verify only the Admin opens the planning pages and faculty see today's classes.

**Module:** Timetable / FR-22, SEC-14

**Preconditions:** Faculty member logged in.

**Parameters:**  F001.

**Steps:** 1: Open Timetable and Semester classes as faculty. 2: Open the Faculty dashboard.

**Expected result:** Both planning pages return 403; the dashboard shows Today's classes.

**Actual result:** Fresh execution on 9 November 2026: 2 mapped test method(s) passed. Assertions cover the automated equivalent described by the named methods; this is not a claim of a separate literal manual execution.

**Result:** PASS automated equivalent

**Evidence:** `artifacts/part3/rerun-2026-11-09/regression.json` (local)

**Exact test methods:**

- `apps.academics.test_planning.PlanningTests.test_only_the_admin_can_open_the_planning_pages`
- `apps.attendance.test_outlook.TodayOverviewTests.test_faculty_dashboard_shows_todays_classes_and_hides_empty_shortage_box`

**Qualification:** Automated equivalent using isolated synthetic fixtures; added with the 9 November 2026 changes (BL-01 D-24 to D-28).

## UT_14_4  Verify the classes-needed calculation reaches the threshold exactly.

**Module:** Attendance Advice / FR-23

**Preconditions:** None (calculation).

**Parameters:**  76/102 at 85%; 3/4 at 80%; 8/10 at 80%; 0/0; 9/10 at 100%; 10/10 at 75%.

**Steps:** 1: Calculate classes needed and classes that can be missed for the listed values.

**Expected result:** 72; 1; 0; 0; none possible; can miss 3.

**Actual result:** Fresh execution on 9 November 2026: 2 mapped test method(s) passed. Assertions cover the automated equivalent described by the named methods; this is not a claim of a separate literal manual execution.

**Result:** PASS automated equivalent

**Evidence:** `artifacts/part3/rerun-2026-11-09/regression.json` (local)

**Exact test methods:**

- `apps.attendance.test_outlook.ClassesNeededTests.test_classes_needed_reaches_the_threshold_exactly`
- `apps.attendance.test_outlook.ClassesNeededTests.test_classes_can_miss_keeps_the_student_at_or_above`

**Qualification:** Automated equivalent using isolated synthetic fixtures; added with the 9 November 2026 changes (BL-01 D-24 to D-28).

## UT_14_5  Verify the advice wording without a semester total.

**Module:** Attendance Advice / FR-23

**Preconditions:** No semester total set.

**Parameters:**  0/0, 3/5, 10/10, 9/10 (100%), 3/4 at 75%.

**Steps:** 1: Build the advice for each value.

**Expected result:** No classes held yet; Attend the next 3 classes to get back to 75%; You can miss 3 classes…; cannot be reached; Attend your next class to stay at 75% or above.

**Actual result:** Fresh execution on 9 November 2026: 1 mapped test method(s) passed. Assertions cover the automated equivalent described by the named methods; this is not a claim of a separate literal manual execution.

**Result:** PASS automated equivalent

**Evidence:** `artifacts/part3/rerun-2026-11-09/regression.json` (local)

**Exact test methods:**

- `apps.attendance.test_outlook.ClassesNeededTests.test_messages_without_a_semester_plan`

**Qualification:** Automated equivalent using isolated synthetic fixtures; added with the 9 November 2026 changes (BL-01 D-24 to D-28).

## UT_14_6  Verify the advice with a semester total, including when the target is out of reach.

**Module:** Attendance Advice / FR-23

**Preconditions:** Semester total of 40 classes.

**Parameters:**  20/25, 30/32 and 5/25 at 75% with 40 planned.

**Steps:** 1: Build the advice for each value.

**Expected result:** Attend at least 10 of the 15 classes left…; already secured 75%; Even attending all 15 classes left gives 50.00%…

**Actual result:** Fresh execution on 9 November 2026: 1 mapped test method(s) passed. Assertions cover the automated equivalent described by the named methods; this is not a claim of a separate literal manual execution.

**Result:** PASS automated equivalent

**Evidence:** `artifacts/part3/rerun-2026-11-09/regression.json` (local)

**Exact test methods:**

- `apps.attendance.test_outlook.ClassesNeededTests.test_messages_with_a_semester_plan`

**Qualification:** Automated equivalent using isolated synthetic fixtures; added with the 9 November 2026 changes (BL-01 D-24 to D-28).

## UT_14_7  Verify semester totals are saved and logged, and invalid values save nothing.

**Module:** Semester Classes / FR-23

**Preconditions:** Admin logged in; three subject offerings.

**Parameters:**  40, blank, 36; 40, abc.

**Steps:** 1: Save 40, blank and 36. 2: Save 40 and abc.

**Expected result:** First save stores the totals with 2 audit entries; second shows "Enter a whole number from 1 to 500" and saves nothing.

**Actual result:** Fresh execution on 9 November 2026: 2 mapped test method(s) passed. Assertions cover the automated equivalent described by the named methods; this is not a claim of a separate literal manual execution.

**Result:** PASS automated equivalent

**Evidence:** `artifacts/part3/rerun-2026-11-09/regression.json` (local)

**Exact test methods:**

- `apps.academics.test_planning.PlanningTests.test_admin_sets_semester_class_totals`
- `apps.academics.test_planning.PlanningTests.test_invalid_semester_totals_save_nothing`

**Qualification:** Automated equivalent using isolated synthetic fixtures; added with the 9 November 2026 changes (BL-01 D-24 to D-28).

## IT_14_2  Verify the student dashboard lists subjects and a subject opens its class-by-class list.

**Module:** Attendance Advice / FR-09, FR-23

**Preconditions:** S001 enrolled in CS101 (40 planned) with 1/3 attended.

**Parameters:**  S001.

**Steps:** 1: Open the Student dashboard. 2: Select the CS101 card. 3: Read the class list.

**Expected result:** Dashboard shows My subjects with 1/3 (33.33%) and no threshold card; the subject page lists each class with date, time and status and says to attend at least 29 of the 37 classes left.

**Actual result:** Fresh execution on 9 November 2026: 2 mapped test method(s) passed. Assertions cover the automated equivalent described by the named methods; this is not a claim of a separate literal manual execution.

**Result:** PASS automated equivalent

**Evidence:** `artifacts/part3/rerun-2026-11-09/regression.json` (local)

**Exact test methods:**

- `apps.attendance.test_outlook.StudentPagesTests.test_dashboard_lists_each_subject_without_the_threshold_card`
- `apps.attendance.test_outlook.StudentPagesTests.test_choosing_a_subject_lists_each_class_with_its_status`

**Qualification:** Automated equivalent using isolated synthetic fixtures; added with the 9 November 2026 changes (BL-01 D-24 to D-28).

## IT_14_3  Verify the Notifications page shows where the student stands and the classes needed.

**Module:** Notifications / FR-14, FR-23

**Preconditions:** S001 below threshold with an alert.

**Parameters:**  S001.

**Steps:** 1: Open Notifications.

**Expected result:** Where you stand now lists CS101 with the classes needed; there is no separate Back to dashboard link at the top.

**Actual result:** Fresh execution on 9 November 2026: 1 mapped test method(s) passed. Assertions cover the automated equivalent described by the named methods; this is not a claim of a separate literal manual execution.

**Result:** PASS automated equivalent

**Evidence:** `artifacts/part3/rerun-2026-11-09/regression.json` (local)

**Exact test methods:**

- `apps.attendance.test_outlook.StudentPagesTests.test_notifications_page_shows_where_the_student_stands`

**Qualification:** Automated equivalent using isolated synthetic fixtures; added with the 9 November 2026 changes (BL-01 D-24 to D-28).
