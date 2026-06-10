---
phase: 01-foundation
reviewed: 2026-06-10T00:00:00Z
depth: standard
files_reviewed: 51
files_reviewed_list:
  - .env.example
  - .gitignore
  - Dockerfile
  - Dockerfile.dev
  - apps/accounts/admin.py
  - apps/accounts/forms.py
  - apps/accounts/migrations/0001_initial.py
  - apps/accounts/migrations/0002_create_groups.py
  - apps/accounts/models.py
  - apps/accounts/services.py
  - apps/accounts/templates/accounts/email/password_reset.html
  - apps/accounts/templates/accounts/email/password_reset_subject.txt
  - apps/accounts/templates/accounts/login.html
  - apps/accounts/templates/accounts/partials/unit_form.html
  - apps/accounts/templates/accounts/partials/unit_row.html
  - apps/accounts/templates/accounts/partials/user_form.html
  - apps/accounts/templates/accounts/partials/user_row.html
  - apps/accounts/templates/accounts/password_reset.html
  - apps/accounts/templates/accounts/password_reset_confirm.html
  - apps/accounts/templates/accounts/password_reset_done.html
  - apps/accounts/templates/accounts/unit_confirm_deactivate.html
  - apps/accounts/templates/accounts/unit_form.html
  - apps/accounts/templates/accounts/unit_list.html
  - apps/accounts/templates/accounts/user_confirm_deactivate.html
  - apps/accounts/templates/accounts/user_form.html
  - apps/accounts/templates/accounts/user_list.html
  - apps/accounts/tests/conftest.py
  - apps/accounts/tests/test_auth.py
  - apps/accounts/tests/test_models.py
  - apps/accounts/tests/test_unit_mgmt.py
  - apps/accounts/tests/test_user_mgmt.py
  - apps/accounts/urls.py
  - apps/accounts/views.py
  - apps/core/models.py
  - apps/core/templates/core/dashboard.html
  - apps/core/urls.py
  - apps/core/views.py
  - config/settings/base.py
  - config/settings/dev.py
  - config/settings/prod.py
  - config/urls.py
  - config/wsgi.py
  - conftest.py
  - docker-compose.prod.yml
  - docker-compose.yml
  - manage.py
  - pytest.ini
  - requirements-dev.txt
  - requirements.txt
  - static/css/main.css
  - templates/base.html
findings:
  critical: 5
  warning: 7
  info: 4
  total: 16
status: issues_found
---

# Phase 01: Code Review Report

**Reviewed:** 2026-06-10T00:00:00Z
**Depth:** standard
**Files Reviewed:** 51
**Status:** issues_found

## Summary

This is the Foundation phase of ComprasNexos: custom User model, organizational unit CRUD, authentication (login/password-reset), admin panel views, and Docker/settings scaffolding. The overall structure is sound — AUTH_USER_MODEL is set correctly, migrations have the right dependency order, and the Django Groups data migration is reversible. However, five blockers were identified that must be resolved before the code ships: an open redirect in login, a logout-via-GET CSRF bypass, an account enumeration leak, a missing CSRF token header on HTMX mutation requests in the admin panel, and a missing password validation bypass in the user creation service. Seven additional warnings cover incomplete permission enforcement, unsafe `next`-parameter redirect, deactivation gaps, and a missing `reportlab` dependency.

---

## Critical Issues

### CR-01: Open Redirect via Unvalidated `next` Parameter

**File:** `apps/accounts/views.py:40`
**Issue:** The login view redirects to `request.GET.get("next", "/")` without any validation. An attacker can craft a link like `/accounts/login/?next=https://evil.com` and after login the user is silently sent to an external site. Django's own `LoginView` uses `url_has_allowed_host_and_scheme` to prevent this — the custom view does not.
**Fix:**
```python
from django.utils.http import url_has_allowed_host_and_scheme

def login_view(request):
    ...
    if form.is_valid():
        user = form.get_user()
        login(request, user)
        next_url = request.GET.get("next", "/")
        if not url_has_allowed_host_and_scheme(
            url=next_url,
            allowed_hosts={request.get_host()},
            require_https=request.is_secure(),
        ):
            next_url = "/"
        return redirect(next_url)
```

---

### CR-02: Logout Executes on GET — No CSRF Protection

**File:** `apps/accounts/views.py:67-70`
**Issue:** `logout_view` calls `logout(request)` unconditionally on any HTTP method, including GET. Any page that loads an `<img src="/accounts/logout/">` or a crawler following links will log the user out. Django's built-in `LogoutView` (Django 5.x) requires POST by default for exactly this reason.
**Fix:**
```python
def logout_view(request):
    if request.method == "POST":
        logout(request)
    return redirect("/accounts/login/")
```
Update the sidebar "Sair" link in `templates/base.html` to use a small `<form method="post">` with `{% csrf_token %}` instead of a bare `<a href>`.

---

### CR-03: Account Enumeration via Differentiated Error Messages

**File:** `apps/accounts/views.py:42-60`
**Issue:** On failed login, the view queries the database to distinguish between "user exists but wrong password" and "user does not exist", then returns different error messages to the browser:
- Inactive account → "Esta conta está inativa."
- Wrong password → "E-mail ou senha incorretos."
- No such user → "E-mail ou senha incorretos." (same text, but the lookup itself is a timing side-channel, and the inactive-account branch leaks that the e-mail IS registered).

The inactive-account branch at line 47 explicitly tells an attacker that a given e-mail address belongs to a real (but inactive) account, enabling targeted credential-stuffing.
**Fix:** Remove the differentiated branch entirely. Return a single generic message for all failure cases, identical to what Django's `AuthenticationForm` already provides. If admins must communicate account status, do it via a separate channel (e.g., the user contacts the admin).
```python
# After form.is_valid() fails — remove the try/except block entirely:
form.add_error(
    None,
    "E-mail ou senha incorretos. Verifique os dados e tente novamente.",
)
```

---

### CR-04: HTMX Mutation Buttons Send No CSRF Token

**File:** `apps/accounts/templates/accounts/partials/user_row.html:18`, `apps/accounts/templates/accounts/partials/unit_row.html:13`
**Issue:** The "Desativar" buttons use `hx-get` to load a confirmation dialog — that is fine, GET carries no CSRF risk. However, the confirmation dialogs (`user_confirm_deactivate.html:6`, `unit_confirm_deactivate.html:6`) use `hx-post` to submit the actual deactivation. HTMX does **not** automatically include the Django CSRF token in AJAX requests unless the token is injected via a `htmx:configRequest` event handler or `hx-headers`.

`base.html` registers the `htmx:configRequest` handler that injects `X-CSRFToken` from the `<meta name="csrf-token">` tag. This is correct **only when the confirm dialog is rendered inside a page that has already loaded `base.html`**. But the confirm dialog partial is injected into `#confirm-container` via HTMX — it is a fragment, not a full page. If HTMX processes the `hx-post` on the confirm button **before** the `htmx:configRequest` listener fires (or if the listener is not present because the partial does not extend `base.html`), the POST will be sent without the CSRF token.

The root problem is that the `htmx:configRequest` handler lives in `base.html:12-18` and is applied globally to `document.body`, so it fires for all HTMX requests — including those initiated by dynamically injected partials. This **does** work correctly in practice today, but it is fragile: the handler depends on `<meta name="csrf-token">` being present in the outer page. The partials themselves contain `{% csrf_token %}` (a hidden input), but HTMX's AJAX path ignores form hidden inputs; it only reads the headers configured via `htmx:configRequest`.

More concretely: the confirm-dialog forms (`user_confirm_deactivate.html`, `unit_confirm_deactivate.html`) do **not** contain `{% csrf_token %}` at all — they rely entirely on the `base.html` meta-tag handler. If the dialog is ever served standalone (e.g., a direct GET to the confirm URL, or a future test), the CSRF header will be absent and Django will reject the POST with 403.

**Fix:** Add `hx-headers='{"X-CSRFToken": "{{ csrf_token }}"}'` directly on each `hx-post` button in the confirmation dialogs so they are self-contained:
```html
<!-- user_confirm_deactivate.html -->
<button
  hx-post="{% url 'accounts:user-deactivate' target_user.pk %}"
  hx-headers='{"X-CSRFToken": "{{ csrf_token }}"}'
  hx-target="#user-row-{{ target_user.pk }}"
  hx-swap="outerHTML"
  class="btn btn-destructive">
  Confirmar desativação
</button>
```
Apply the same pattern to `unit_confirm_deactivate.html`.

---

### CR-05: Password Validation Validators Bypassed in `create_user` Service

**File:** `apps/accounts/services.py:11-30`
**Issue:** `create_user` calls `user.set_password(password)` directly without running Django's `AUTH_PASSWORD_VALIDATORS`. The validators defined in `base.py` (lines 77-82) — minimum length, common passwords, numeric-only check — are configured in settings but are **never invoked** by this code path. An admin can create a user with password `"1"` and it will be accepted silently.

`UserCreateForm` has no `clean_password1` that calls `validate_password`, and the service layer does not call it either. The password validators are only enforced if `validate_password()` is explicitly called.
**Fix:** In `services.py`, call `validate_password` before `set_password`:
```python
from django.contrib.auth.password_validation import validate_password

def create_user(data: dict) -> User:
    password = data.pop("password1", None) or data.pop("password", None)
    data.pop("password2", None)

    user = User(**data)
    if password:
        validate_password(password, user)  # raises ValidationError if invalid
        user.set_password(password)
    user.save()
    ...
```
Also add a `clean_password1` method to `UserCreateForm` (or use `SetPasswordForm` as a base) to surface validation errors in the form UI rather than as a 500 in the view.

---

## Warnings

### WR-01: `UserDeactivateView` and `UnitDeactivateView` Are Missing `AdminRequiredMixin` Permission Enforcement via POST-Only Guard

**File:** `apps/accounts/views.py:193-202` and `292-301`
**Issue:** Both deactivation views inherit `AdminRequiredMixin` and correctly block non-admins. However, neither view has a GET handler defined. `View.dispatch` will call `http_method_not_allowed` for GET requests — this returns a 405, not a redirect, which is acceptable. But consider: an attacker who IS an admin could accidentally deactivate a user by triggering a GET (e.g., a browser prefetch). More importantly, there is no guard preventing an admin from self-deactivating their own account. `deactivate_user` in `services.py` accepts `actor` as a parameter but never uses it to prevent self-deactivation.

If the only admin deactivates themselves, the system has no remaining admin account and no recovery path short of a direct database edit.
**Fix:** Add a self-deactivation guard in `services.py`:
```python
def deactivate_user(user: User, actor: User) -> User:
    if user.pk == actor.pk:
        raise ValueError("An admin cannot deactivate their own account.")
    user.is_active = False
    user.save(update_fields=["is_active"])
    return user
```
Propagate this error to the view as a user-facing message.

---

### WR-02: `services.create_user` Mutates the Caller's Dict

**File:** `apps/accounts/services.py:16-18`
**Issue:** `create_user` calls `data.pop("password1")`, `data.pop("password")`, and `data.pop("password2")` on the dict passed in. The caller passes `form.cleaned_data` — a `dict` that Django's form machinery may read again after the call (e.g., for logging or rendering a confirmation page). Mutating a caller's dict is an unexpected side-effect.
**Fix:** Operate on a copy:
```python
def create_user(data: dict) -> User:
    data = dict(data)  # defensive copy
    password = data.pop("password1", None) or data.pop("password", None)
    data.pop("password2", None)
    ...
```

---

### WR-03: `UserCreateForm` Does Not Enforce Password Minimum Length in the Form Layer

**File:** `apps/accounts/forms.py:11-29`
**Issue:** `UserCreateForm` uses bare `forms.CharField` for `password1` and `password2` — no `min_length`, no call to `validate_password`. A zero-character password would pass form validation (only the mismatch check exists). This is related to CR-05 but is independently fixable at the form layer.
**Fix:** Add explicit validation in the form's `clean` method, or replace the password fields with Django's `SetPasswordForm` approach:
```python
from django.contrib.auth.password_validation import validate_password

def clean(self):
    cleaned_data = super().clean()
    p1 = cleaned_data.get("password1")
    p2 = cleaned_data.get("password2")
    if p1 and p2 and p1 != p2:
        raise forms.ValidationError("As senhas não coincidem. Tente novamente.")
    if p1:
        # Surface validator errors in the form
        try:
            validate_password(p1)
        except forms.ValidationError as e:
            self.add_error("password1", e)
    return cleaned_data
```

---

### WR-04: `ALLOWED_HOSTS = []` in `base.py` — Production Will Silently Fail if Env Var Is Absent

**File:** `config/settings/base.py:15`
**Issue:** `base.py` sets `ALLOWED_HOSTS = []`, which denies all requests. `prod.py` overrides this via `config("ALLOWED_HOSTS", cast=...)`. If `ALLOWED_HOSTS` env var is missing in production, `decouple.config()` raises `UndefinedValueError` at startup — which is actually a safe failure mode. However, if a dev accidentally runs with `DJANGO_SETTINGS_MODULE=config.settings.base` (possible during debugging), the empty list will silently block all requests and the error is confusing.

More importantly, `config/wsgi.py:8` sets `os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.prod")`. If the environment variable is not set and `prod.py` is used, but `ALLOWED_HOSTS` env var is also not set, Django raises an unhandled `UndefinedValueError` during WSGI startup — not a clean Django 400. This will produce a 500 with no useful error page in production.
**Fix:** Add a fallback default that makes the failure obvious at request time rather than at import time, or document that `ALLOWED_HOSTS` is required. At minimum, update `base.py` to avoid the base-settings footgun:
```python
# base.py — do not use base settings directly in production
ALLOWED_HOSTS: list[str] = []  # overridden by dev.py and prod.py
```
In `dev.py`, explicitly add:
```python
ALLOWED_HOSTS = ["localhost", "127.0.0.1", "0.0.0.0"]
```

---

### WR-05: `docker-compose.prod.yml` Has No Volume Mount — Static Files Are Served from Inside Container

**File:** `docker-compose.prod.yml:6-15`
**Issue:** The production compose file has no named volume or bind-mount for `staticfiles/`. Static files are collected into the image at build time (`collectstatic` runs in `Dockerfile:18-24`) and served by WhiteNoise from inside the container. This means every deployment rebuilds static files into the image — which is correct for WhiteNoise's `CompressedManifestStaticFilesStorage`. However, media file uploads (when those features are built in later phases) have no declared volume, meaning uploaded files will be lost on container restart. This is a future time-bomb to be noted now.

Additionally, there is no `SECURE_HSTS_SECONDS`, `SECURE_HSTS_INCLUDE_SUBDOMAINS`, or `SECURE_PROXY_SSL_HEADER` set in `prod.py`. For an internal app behind a load balancer or reverse proxy, `SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")` is required for `request.is_secure()` to return True, which in turn affects CSRF cookie security and `SESSION_COOKIE_SECURE`.
**Fix:** Add to `prod.py`:
```python
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
```
Add a media volume to `docker-compose.prod.yml` when file uploads are introduced (Phase 3+).

---

### WR-06: `unit_row.html` Uses `unit.user_count` — Attribute Not Present When Partial Is Returned After Deactivation

**File:** `apps/accounts/templates/accounts/partials/unit_row.html:9`
**Issue:** `unit_row.html` renders `{{ unit.user_count }}`. This annotation is added by `UnitListView.get_queryset()` via `annotate(user_count=Count("default_users"))`. When `UnitDeactivateView.post()` (line 292-301 in `views.py`) returns the updated partial, it passes `{"unit": unit}` directly without re-annotating. The template will raise a `VariableDoesNotExist` silently (Django's template engine does not raise on missing attributes — it renders empty string), so the user count column shows blank after a deactivation.
**Fix:** In `UnitDeactivateView.post()`, add the annotation before passing to template:
```python
from django.db.models import Count

def post(self, request, pk):
    unit = get_object_or_404(UnidadeOrganizacional, pk=pk)
    unit.ativo = False
    unit.save()
    unit = UnidadeOrganizacional.objects.annotate(
        user_count=Count("default_users")
    ).get(pk=pk)
    return render(request, "accounts/partials/unit_row.html", {"unit": unit})
```

---

### WR-07: `UserUpdateView` Does Not Sync Django Group Membership When Role Changes

**File:** `apps/accounts/views.py:161-180`
**Issue:** `UserUpdateView.post()` calls `form.save()` directly (which calls `User.save()`). This updates the `role` field on the model but does **not** update the user's Django Group membership. `services.create_user` correctly assigns a group on creation, but `UserEditForm` + `form.save()` bypass the service layer entirely. After editing a user's role from "Solicitante" to "Comprador", `user.groups.all()` will still list "Solicitante", breaking any permission check that relies on groups.
**Fix:** Extract an `update_user` service function that mirrors `create_user`:
```python
def update_user(user: User, data: dict) -> User:
    for attr, value in data.items():
        setattr(user, attr, value)
    user.save()
    # Resync group membership
    user.groups.clear()
    role_display = user.get_role_display()
    group, _ = Group.objects.get_or_create(name=role_display)
    user.groups.add(group)
    return user
```
Call `services.update_user(target_user, form.cleaned_data)` in `UserUpdateView.post()` instead of `form.save()`.

---

## Info

### IN-01: `logout_view` Uses Hardcoded URL String Instead of `reverse()`

**File:** `apps/accounts/views.py:70`
**Issue:** `redirect("/accounts/login/")` hardcodes the URL path. If the URL prefix changes, this silently breaks. The URL pattern is already named `accounts:login`.
**Fix:**
```python
from django.urls import reverse
return redirect(reverse("accounts:login"))
```

---

### IN-02: `reportlab` Is Missing from `requirements.txt`

**File:** `requirements.txt`
**Issue:** `CLAUDE.md` lists `reportlab` as a client-mandated dependency and it is documented as required for PDF generation (`apps/relatorios/pdf.py` in later phases). It is absent from `requirements.txt`. This will cause an `ImportError` the moment any PDF view is implemented.
**Fix:** Add `reportlab` to `requirements.txt`:
```
reportlab
```

---

### IN-03: `hx-get=""` on Cancel Buttons Sends a GET to the Current Page

**File:** `apps/accounts/templates/accounts/user_confirm_deactivate.html:7`, `apps/accounts/templates/accounts/unit_confirm_deactivate.html:7`
**Issue:** The "Cancelar" buttons use `hx-get=""` which in HTMX resolves to the current URL. When the confirm dialog partial is injected inside `unit_list.html`, the current URL is `/accounts/admin-panel/unidades/`. An HTMX GET to `""` will fetch the full page HTML and swap it into `#confirm-container` — rendering the entire page inside a `<div>`. This produces broken layout and is likely unintentional. The intent appears to be "clear the confirm container".
**Fix:** Use `hx-get` returning an empty fragment response, or simply clear with JavaScript:
```html
<!-- Option A: inline click handler to clear -->
<button type="button" onclick="document.getElementById('confirm-container').innerHTML=''" class="btn btn-secondary">Cancelar</button>

<!-- Option B: point to a dedicated empty-fragment view -->
<button hx-get="{% url 'core:empty-fragment' %}" hx-target="#confirm-container" hx-swap="innerHTML" class="btn btn-secondary">Cancelar</button>
```

---

### IN-04: `pytest-cov` Absent from `requirements-dev.txt`

**File:** `requirements-dev.txt`
**Issue:** The dev requirements include `pytest` and `pytest-django` but not `pytest-cov`. Coverage measurement is standard practice for a project at this stage. Not a runtime bug, but a gap in tooling completeness.
**Fix:**
```
pytest-cov
```
Add `--cov=apps --cov-report=term-missing` to `pytest.ini`'s `addopts` line.

---

_Reviewed: 2026-06-10T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
