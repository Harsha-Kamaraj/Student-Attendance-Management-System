\# BL-30: Verify Usability and Browser Compatibility



\## 1. Objective



Verify that the Student Attendance Management System is understandable and usable across the Admin, Faculty, and Student roles, with appropriate form validation, responsive layouts, clear feedback messages, and understandable empty states.



\## 2. Supported Browser and Device Targets



The project's compatibility target, as defined in the existing decision log, is the latest two versions of Chrome, Microsoft Edge, Firefox, and Safari on desktop, plus usability at a 360px viewport on Chrome for Android and Safari on iOS.



| Browser or device | Target | Verification status |

|---|---|---|

| Google Chrome — desktop | Latest two versions | Pending manual verification |

| Microsoft Edge — desktop | Latest two versions | Pending manual verification |

| Mozilla Firefox — desktop | Latest two versions | Pending manual verification |

| Apple Safari — desktop | Latest two versions | Pending manual verification |

| Chrome — Android | 360px-wide viewport | Pending manual verification |

| Safari — iOS | 360px-wide viewport | Pending manual verification |



A browser or device is considered verified only after the application has been opened and the relevant workflows have been tested in that environment.



\## 3. Role-Based Workflow Verification



\### Admin

\- Open the Admin dashboard.

\- Navigate to account and academic management pages.

\- Check form labels, required-field validation, tables, buttons, and feedback messages.

\- Verify that empty lists provide understandable feedback.

\- Check that management actions produce clear success or error messages.



\### Faculty

\- Open the Faculty dashboard.

\- View assigned classes and enrolled students.

\- Open the attendance-marking page.

\- Verify that missing attendance statuses and invalid submissions produce understandable errors.

\- Check that saved attendance produces clear feedback.

\- Verify table usability and empty-roster messaging.



\### Student

\- Open the Student dashboard.

\- Open the attendance summary.

\- Verify the display of attendance percentages and subject details.

\- Apply subject and date filters.

\- Confirm that invalid date ranges produce understandable errors.

\- Confirm that filters returning no records display a clear empty-state message.



\## 4. Automated Usability and Validation Coverage



Existing automated tests cover several relevant behaviours:



\- Login rejects blank required fields.

\- Invalid login credentials produce a consistent error message.

\- Admin, Faculty, and Student users reach their respective dashboards.

\- Account creation rejects missing required fields and invalid email addresses.

\- Attendance marking rejects missing student statuses and invalid status values.

\- Student attendance summaries show an empty state when no classes or matching records exist.

\- Reversed date ranges produce a validation message.

\- Access restrictions prevent users from opening pages outside their authorised roles.



These existing tests should be reused rather than duplicated.



\## 5. Responsive Design and Accessibility Checks



During manual verification:



\- Confirm that the page viewport adapts to the device width.

\- Check that navigation, buttons, forms, and messages remain readable at 360px.

\- Check that tables do not force the entire page to overflow horizontally.

\- Confirm that form labels identify their associated inputs.

\- Confirm that validation errors are visible and understandable.

\- Confirm that success and error messages are noticeable.

\- Check that empty lists and reports explain when no data is available.



\## 6. Defect and Retest Log



Record each defect found during verification with its page, browser/device, steps to reproduce, expected result, actual result, fix, and retest outcome.



No defect should be marked as fixed without verifying the relevant workflow again.



\## 7. Final Verification Results



The final report must record:

\- Automated tests executed and their results.

\- Manual workflows verified for each role.

\- Browser versions and viewport sizes actually tested.

\- Defects discovered and their fixes.

\- Retest results and any remaining limitations.



Browser compatibility must not be marked fully verified until the target environments have been tested.
## 8. Test Execution Results



\### Automated Tests



The following targeted Django tests were executed after the responsive navigation update:



```text

python manage.py test apps.accounts.tests.LoginTests apps.attendance.test\_summary apps.attendance.test\_marking

```



Results:

\- Tests discovered: 28

\- Tests passed: 28

\- Tests failed: 0

\- Django system check: No issues identified

\- `git diff --check`: Passed with no reported errors



\### Responsive Navigation Update



The shared base template was updated to improve navigation layout on narrow screens. Flex wrapping, spacing, and small-screen layout adjustments were introduced for the navigation controls.



The targeted automated tests passed after the update. Manual verification at the target viewport sizes and across the supported browsers remains pending.



\### Remaining Verification



The latest two versions of Chrome, Microsoft Edge, Firefox, and Safari on desktop, along with Chrome on Android and Safari on iOS at a 360px viewport, must be tested before full browser compatibility can be confirmed.



The Admin, Faculty, and Student workflows must also be manually checked for layout usability, form validation, readable messages, and understandable empty states.



No browser or device is marked as manually verified until testing has actually been completed.

