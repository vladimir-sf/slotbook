# E2E tests (planned)

QA/Platform agent adds Playwright test runner here and covers:
- public activities -> available slot -> create booking -> confirmation
- concurrent same-slot requests: exactly one success and one HTTP 409
- admin login, activities/window setup, blocked date, cancel booking
- proper behavior across daylight-saving boundaries

These tests are NOT included in the initial scaffold.
