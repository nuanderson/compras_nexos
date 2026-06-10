---
phase: 1
slug: foundation
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-06-10
---

# Phase 1 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest + pytest-django |
| **Config file** | `pytest.ini` (Wave 0 installs) |
| **Quick run command** | `docker compose run --rm web pytest accounts/ --tb=short -q` |
| **Full suite command** | `docker compose run --rm web pytest --tb=short -q` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `docker compose run --rm web pytest accounts/ --tb=short -q`
- **After every plan wave:** Run `docker compose run --rm web pytest --tb=short -q`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| AUTH-01 | 01 | 1 | AUTH-01 | — | Login rejects invalid credentials with 401 | unit | `docker compose run --rm web pytest accounts/tests/test_auth.py -q` | ❌ W0 | ⬜ pending |
| AUTH-02 | 01 | 2 | AUTH-02 | — | Password reset link expires after 24h | unit | `docker compose run --rm web pytest accounts/tests/test_password_reset.py -q` | ❌ W0 | ⬜ pending |
| AUTH-03 | 01 | 1 | AUTH-03 | — | Session persists across browser refresh | manual | See Manual Verifications | — | ⬜ pending |
| AUTH-04 | 01 | 2 | AUTH-04 | — | Only Admin can create/deactivate users | unit | `docker compose run --rm web pytest accounts/tests/test_admin.py -q` | ❌ W0 | ⬜ pending |
| AUTH-05 | 01 | 1 | AUTH-05 | — | User assigned to wrong group cannot access restricted views | unit | `docker compose run --rm web pytest accounts/tests/test_permissions.py -q` | ❌ W0 | ⬜ pending |
| AUTH-06 | 01 | 2 | AUTH-06 | — | Requisition form pre-fills user's default unit | unit | `docker compose run --rm web pytest accounts/tests/test_unit_default.py -q` | ❌ W0 | ⬜ pending |
| UNIT-01 | 01 | 2 | UNIT-01 | — | Admin can create/edit/deactivate units | unit | `docker compose run --rm web pytest accounts/tests/test_units.py -q` | ❌ W0 | ⬜ pending |
| UNIT-02 | 01 | 2 | UNIT-02 | — | Admin can assign users to units | unit | `docker compose run --rm web pytest accounts/tests/test_units.py -q` | ❌ W0 | ⬜ pending |
| UNIT-03 | 01 | 2 | UNIT-03 | — | Default unit pre-selected on requisition form | unit | `docker compose run --rm web pytest accounts/tests/test_unit_default.py -q` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `accounts/tests/__init__.py` — package marker
- [ ] `accounts/tests/conftest.py` — shared fixtures (test users per role, test units)
- [ ] `accounts/tests/test_auth.py` — stubs for AUTH-01, AUTH-02, AUTH-03
- [ ] `accounts/tests/test_permissions.py` — stubs for AUTH-05
- [ ] `accounts/tests/test_admin.py` — stubs for AUTH-04
- [ ] `accounts/tests/test_units.py` — stubs for UNIT-01, UNIT-02
- [ ] `accounts/tests/test_unit_default.py` — stubs for AUTH-06, UNIT-03
- [ ] `pytest.ini` — `DJANGO_SETTINGS_MODULE=compras_nexos.settings.test`
- [ ] `pytest-django` in `requirements-dev.txt`

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Session persists across browser refresh | AUTH-03 | Django session handling — browser behavior cannot be asserted in unit tests | 1. Log in. 2. Close and reopen browser tab. 3. Confirm still authenticated. |
| Dark theme renders correctly | UI-SPEC | CSS rendering requires visual inspection | 1. Open login page. 2. Confirm #1a1a2e background, #e94560 CTA button. |
| Role-based nav items visible/hidden | AUTH-05 | Full page render with different users | 1. Log in as each role. 2. Confirm only permitted nav items visible. |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
