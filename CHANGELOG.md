# Changelog

## 1.1.4 — 2026-10-30

- Explain quota-read failures without exposing internal codes in the dashboard; show current connection failures in Settings and preserve raw diagnostics.
- Translate native notification titles and bodies before Qt delivery using the current UI language.
- Add disconnection/recovery and signal-to-notification regression coverage.

## 1.1.3 — 2026-10-23

- Complete Chinese operational, background-error, update, dialog, history and tray translations.
- Preserve model labels during language switching and provide a Chinese fallback for foreign-language release notes.
- Add state-driven localization coverage to the release gate: all 25 dashboard branches, 192 self-test combinations and 654 source messages; 428 checks pass.

## 1.1.2 — 2026-10-21

- Remove the Windows main-window caption icon while keeping the in-app brand mark, taskbar/tray icons and normal window controls.

## 1.1.1 — 2026-10-21

- Translate blocked/inconclusive provider checks and related error states in Chinese, including combined tray and tooltip messages.
- Use the Peach Blossom accent for warning stripes while retaining warning badges, icons and safety behavior.
- Add an actual-widget localization regression; 420 release checks pass.

## 1.1.0 — 2026-10-21

- Add independent Classic Mint / Peach Blossom theme colors with system, light and dark modes.
- Redesign the dashboard, quota bars, action icons and responsive card layout.
- Simplify the automation card while retaining daily time editing and tray pause controls.
- Improve saved/unsaved feedback, automatic-sync tooltips and version formatting.
- Preserve schedules and history; verify 419 release checks and 96 UI combinations.

## 1.0.1 — 2026-10-20

- Remove automatic reset-boundary chaining. Automatic warm-up is admitted only through the saved daily appointments queue.
- Default new installations to daily time slots. Upgrade legacy continuous configurations with automation off and obsolete pending slots cleared; preserve existing multi-time plans and history.
- Keep reset-aware waiting for an already admitted scheduled appointment, duplicate prevention, read-only quota sync and manual self-tests.
- Add six focused regressions and update the release build to derive asset names from the product version.

## 1.0.0 — 2026-10-20

First published release: daily appointments, read-only quota refresh, request self-tests, Chinese/English UI, light/dark themes and a Windows Setup installer.
