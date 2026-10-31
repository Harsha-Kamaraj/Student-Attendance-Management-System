# BL-30: Verify Usability and Browser Compatibility

## 1. Objective

Verify that the Student Attendance Management System is understandable and usable across the Admin, Faculty, and Student roles, with appropriate form validation, responsive layouts, clear feedback messages, and understandable empty states.

## 2. Supported Browser and Device Targets

The project's compatibility target is the latest two versions of Google Chrome, Microsoft Edge, Mozilla Firefox, and Apple Safari on desktop, along with usability at a 360px-wide viewport for Chrome on Android and Safari on iOS.

| Browser or Device | Target | Verification Status |
|---|---|---|
| Google Chrome - Desktop | Available development environment | Manually tested |
| Microsoft Edge - Desktop | Latest supported versions | Not manually tested in this environment |
| Mozilla Firefox - Desktop | Latest supported versions | Not manually tested in this environment |
| Apple Safari - Desktop | Latest supported versions | Not manually tested in this environment |
| Chrome - Android | 360px-wide viewport | Responsive layout manually checked |
| Safari - iOS | 360px-wide viewport | Not manually tested on a physical iOS device |

A browser or device should only be marked as fully verified after the application has been opened and the relevant workflows have been tested in that environment.

## 3. Role-Based Workflow Verification

### Admin Workflow

The Admin workflow was manually checked for dashboard usability and responsive layout.

Verified:

- Admin dashboard loads correctly.
- Navigation and dashboard content remain readable.
- Buttons and controls remain accessible.
- Dashboard content remains usable at a narrow mobile-sized viewport.
- No blocking layout issue was observed during the manual test.

Status: **Verified in the manually tested development environment.**

### Faculty Workflow

The Faculty workflow was manually checked for dashboard usability and responsive layout.

Verified:

- Faculty dashboard loads correctly.
- Assigned-class and attendance-related information remains readable.
- Dashboard cards and long text wrap correctly on narrow screens.
- Buttons and navigation remain accessible.
- Attendance-related information remains readable.
- No unwanted page-level horizontal overflow was observed during testing.

Status: **Verified in the manually tested development environment.**

### Student Workflow

The Student workflow was manually checked after logging in as a Student user.

Verified:

- Student dashboard loads correctly.
- Overall attendance percentage is displayed correctly.
- Attendance threshold information is visible.
- Student navigation links work correctly.
- Student profile navigation was checked.
- Attendance summary navigation was checked.
- Notification navigation was checked.
- The layout remains readable and usable at a narrow mobile-sized viewport.

Status: **Verified in the manually tested development environment.**

## 4. Automated Usability and Validation Coverage

Existing automated tests cover several relevant behaviours:

- Login rejects blank required fields.
- Invalid login credentials produce a consistent error message.
- Admin, Faculty, and Student users reach their respective dashboards.
- Account creation rejects missing required fields and invalid email addresses.
- Attendance marking rejects missing student statuses and invalid status values.
- Student attendance summaries show an empty state when no classes or matching records exist.
- Reversed date ranges produce a validation message.
- Access restrictions prevent users from opening pages outside their authorised roles.

These existing tests were reused rather than unnecessarily duplicated.

## 5. Automated Test Execution Results

The following targeted Django tests were executed after the BL-30 responsive layout update:

```text
python manage.py test apps.accounts.tests.LoginTests apps.attendance.test_summary apps.attendance.test_marking
```

Results:

- Tests discovered: 28
- Tests passed: 28
- Tests failed: 0
- Django system check: No issues identified
- Test database was created and destroyed successfully
- `git diff --check` was executed without reported whitespace errors before the earlier implementation commit

Result: **PASS**

## 6. Responsive Design and Accessibility Checks

Manual responsive testing was performed using a narrow mobile-sized viewport of approximately 360px.

The following were checked:

- The page viewport adapts to the available width.
- Navigation remains readable.
- Navigation controls wrap appropriately on narrow screens.
- Dashboard cards remain within the viewport.
- Long text wraps instead of overflowing outside the screen.
- Buttons remain visible and accessible.
- Attendance information remains readable.
- User information in the navigation remains readable.
- Images and SVG content are constrained to the available width.
- No significant horizontal page overflow was observed in the manually tested Admin, Faculty, and Student workflows.

The shared base template includes responsive handling for:

- Mobile viewport sizing.
- Text-size adjustment.
- Image and SVG maximum width.
- Responsive table handling.
- Long text wrapping.
- Flexible navigation controls.
- Small-screen navigation layout.

Status: **Verified for the manually tested workflows.**

## 7. Form Validation and User Feedback

The system provides validation and feedback through existing application workflows and automated tests.

The following behaviours were covered:

- Required login fields are validated.
- Invalid login credentials produce an error message.
- Missing attendance statuses are rejected.
- Invalid attendance status values are rejected.
- Invalid date ranges produce an understandable validation message.
- Empty attendance results display an understandable empty-state message.
- Role restrictions prevent unauthorised users from accessing protected workflows.
- Dashboard and workflow information remains readable during the tested responsive layout checks.

Status: **Verified through automated tests and manual workflow checks.**

## 8. Defect and Retest Log

### Defect 1: Narrow-Screen Navigation and Text Layout

**Area:** Shared navigation and dashboard layout

**Problem:** Long navigation text and dashboard content required improved handling on narrow mobile-sized screens.

**Fix:** Responsive CSS was added to the shared base template to:

- Allow navigation controls to wrap.
- Improve small-screen spacing.
- Prevent long text from causing unnecessary overflow.
- Keep images and SVG elements within the viewport.
- Improve readability of user information and navigation controls.

**Retest:** Admin, Faculty, and Student workflows were manually checked after the update.

**Result:** PASS

### Defect 2: Faculty Dashboard Rendering Error

**Area:** Faculty dashboard

**Problem:** A template URL namespace reference caused a `NoReverseMatch` error during testing.

**Fix:** The shared base template was corrected to use valid URL references available in the project configuration.

**Retest:** The Faculty dashboard was opened again successfully.

**Result:** PASS

## 9. Manual Verification Summary

The following workflows were manually tested successfully:

| Workflow | Result |
|---|---|
| Admin dashboard | PASS |
| Faculty dashboard | PASS |
| Student dashboard | PASS |
| Student profile navigation | PASS |
| Student attendance navigation | PASS |
| Student notifications navigation | PASS |
| Login and logout workflow | PASS |
| Password change workflow | PASS |
| Narrow mobile-sized responsive layout | PASS |

No blocking usability issues were observed during the final manual retest of the tested workflows.

## 10. Browser Compatibility Status

The application was manually tested in the available local development browser environment.

The responsive layout was also checked using a narrow mobile-sized viewport of approximately 360px.

The following conclusions can be made:

- The manually tested Admin workflow is usable.
- The manually tested Faculty workflow is usable.
- The manually tested Student workflow is usable.
- Navigation and dashboard content remain readable at the tested narrow viewport.
- The targeted automated tests pass successfully.

### Remaining Cross-Browser Limitation

Full certification across all target environments requires separate testing in:

- Microsoft Edge.
- Mozilla Firefox.
- Apple Safari.
- Chrome on a physical Android environment.
- Safari on a physical iOS environment.

Those environments should only be marked as fully verified after actual testing in those browsers or devices.

## 11. Final Verification Result

BL-30 usability verification has been completed for the manually tested Admin, Faculty, and Student workflows.

Automated validation results:

**28 tests passed, 0 tests failed.**

Manual verification confirmed that:

- Admin workflow is usable.
- Faculty workflow is usable.
- Student workflow is usable.
- Login and logout workflows function correctly.
- Student navigation links function correctly.
- Password change functionality works.
- Responsive navigation and dashboard layouts remain usable at a narrow mobile-sized viewport.

No blocking usability issues were observed during the final retest of the manually tested workflows.

### Final Status

**BL-30 implementation and verification: COMPLETED for the tested local development environment.**

Full cross-browser certification remains dependent on testing in each additional target browser and physical device environment.