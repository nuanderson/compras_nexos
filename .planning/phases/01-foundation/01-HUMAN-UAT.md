---
status: partial
phase: 01-foundation
source: [01-VERIFICATION.md]
started: 2026-06-10
updated: 2026-06-10
---

## Current Test

[awaiting human testing]

## Tests

### 1. Login page visual appearance + authentication flow
expected: Dark theme renders (#1a1a2e background, #e94560 CTA button). Valid credentials redirect to `/`. Invalid credentials show error message without revealing whether email exists.
result: [pending]

### 2. Password reset email delivery
expected: Clicking "Redefinir senha" on `/accounts/password-reset/` with a registered email causes an email to appear in the Docker console log with correct subject ("Redefinição de senha — ComprasNexos" or similar) and a valid reset link.
result: [pending]

### 3. Admin panel role-based access
expected: Logged-in admin navigates to `/admin-panel/usuarios/` and sees user list (HTTP 200). Logged-in Solicitante navigating to same URL receives HTTP 403.
result: [pending]

### 4. HTMX inline deactivation flow
expected: On the user list page, clicking "Desativar" for a user causes a confirmation card to appear inline (no full page reload). Clicking "Confirmar desativação" deactivates the user and updates the row inline showing "Inativo" badge — still no full page reload.
result: [pending]

### 5. Unit deactivation user_count column (WR-06 check)
expected: After deactivating a unit via the HTMX flow, the "Usuários vinculados" column in the unit row shows a number (or 0), not blank. This verifies WR-06 from the code review is benign or needs fixing.
result: [pending]

## Summary

total: 5
passed: 0
issues: 0
pending: 5
skipped: 0
blocked: 0

## Gaps
