"""
Accounts views: login, logout, password reset, and admin panel CRUD.
Admin panel views (UserListView, UserCreateView, etc.) are at the bottom.
"""
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import (
    PasswordResetConfirmView,
    PasswordResetDoneView,
    PasswordResetView,
)
from django.core.exceptions import PermissionDenied
from django.db.models import Count
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views import View
from django.views.generic import ListView

from . import services
from .forms import UnidadeForm, UserCreateForm, UserEditForm
from .models import UnidadeOrganizacional, User


# ──────────────────────────────────────────────────────────────────────────────
# Auth views
# ──────────────────────────────────────────────────────────────────────────────


def login_view(request):
    """Login with email + password. Uses Django AuthenticationForm."""
    if request.user.is_authenticated:
        return redirect("/")

    if request.method == "POST":
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect(request.GET.get("next", "/"))
        else:
            # Check if user exists but is inactive
            username = request.POST.get("username", "")
            try:
                existing_user = User.objects.get(email=username)
                if not existing_user.is_active:
                    form.add_error(
                        None,
                        "Esta conta está inativa. Entre em contato com o administrador do sistema.",
                    )
                else:
                    form.add_error(
                        None,
                        "E-mail ou senha incorretos. Verifique os dados e tente novamente.",
                    )
            except User.DoesNotExist:
                form.add_error(
                    None,
                    "E-mail ou senha incorretos. Verifique os dados e tente novamente.",
                )
    else:
        form = AuthenticationForm()

    return render(request, "accounts/login.html", {"form": form})


def logout_view(request):
    """Log out the current user and redirect to login."""
    logout(request)
    return redirect("/accounts/login/")


password_reset_view = PasswordResetView.as_view(
    template_name="accounts/password_reset.html",
    email_template_name="accounts/email/password_reset.html",
    subject_template_name="accounts/email/password_reset_subject.txt",
    success_url="/accounts/password-reset/done/",
)

password_reset_done_view = PasswordResetDoneView.as_view(
    template_name="accounts/password_reset_done.html",
)

password_reset_confirm_view = PasswordResetConfirmView.as_view(
    template_name="accounts/password_reset_confirm.html",
    success_url="/accounts/login/",
)


# ──────────────────────────────────────────────────────────────────────────────
# Admin panel permission mixin
# ──────────────────────────────────────────────────────────────────────────────


class AdminRequiredMixin(LoginRequiredMixin):
    """Restrict access to users with role='admin' or is_superuser=True."""

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if request.user.role != "admin" and not request.user.is_superuser:
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)


# ──────────────────────────────────────────────────────────────────────────────
# User management views
# ──────────────────────────────────────────────────────────────────────────────


class UserListView(AdminRequiredMixin, ListView):
    model = User
    template_name = "accounts/user_list.html"
    context_object_name = "users"

    def get_queryset(self):
        return User.objects.select_related("default_unit").order_by("email")


class UserCreateView(AdminRequiredMixin, View):
    def get(self, request):
        form = UserCreateForm()
        return render(
            request,
            "accounts/user_form.html",
            {"form": form, "action": "create", "page_title": "Criar Usuário"},
        )

    def post(self, request):
        form = UserCreateForm(request.POST)
        if form.is_valid():
            services.create_user(form.cleaned_data)
            if request.htmx:
                from django_htmx.http import HttpResponseClientRedirect

                return HttpResponseClientRedirect(reverse("accounts:user-list"))
            return redirect("accounts:user-list")
        template = (
            "accounts/partials/user_form.html"
            if request.htmx
            else "accounts/user_form.html"
        )
        return render(request, template, {"form": form, "action": "create"})


class UserUpdateView(AdminRequiredMixin, View):
    def get(self, request, pk):
        target_user = get_object_or_404(User, pk=pk)
        form = UserEditForm(instance=target_user)
        return render(
            request,
            "accounts/user_form.html",
            {
                "form": form,
                "action": "edit",
                "target_user": target_user,
                "page_title": "Editar Usuário",
            },
        )

    def post(self, request, pk):
        target_user = get_object_or_404(User, pk=pk)
        form = UserEditForm(request.POST, instance=target_user)
        if form.is_valid():
            form.save()
            if request.htmx:
                from django_htmx.http import HttpResponseClientRedirect

                return HttpResponseClientRedirect(reverse("accounts:user-list"))
            return redirect("accounts:user-list")
        template = (
            "accounts/partials/user_form.html"
            if request.htmx
            else "accounts/user_form.html"
        )
        return render(
            request,
            template,
            {"form": form, "action": "edit", "target_user": target_user},
        )


class UserDeactivateConfirmView(AdminRequiredMixin, View):
    def get(self, request, pk):
        target_user = get_object_or_404(User, pk=pk)
        return render(
            request,
            "accounts/user_confirm_deactivate.html",
            {"target_user": target_user},
        )


class UserDeactivateView(AdminRequiredMixin, View):
    def post(self, request, pk):
        target_user = get_object_or_404(User, pk=pk)
        services.deactivate_user(target_user, actor=request.user)
        # Return updated row partial for HTMX outerHTML swap
        return render(
            request,
            "accounts/partials/user_row.html",
            {"user": target_user},
        )


# ──────────────────────────────────────────────────────────────────────────────
# Unit management views
# ──────────────────────────────────────────────────────────────────────────────


class UnitListView(AdminRequiredMixin, ListView):
    model = UnidadeOrganizacional
    template_name = "accounts/unit_list.html"
    context_object_name = "units"

    def get_queryset(self):
        return UnidadeOrganizacional.objects.annotate(
            user_count=Count("default_users")
        ).order_by("nome")


class UnitCreateView(AdminRequiredMixin, View):
    def get(self, request):
        form = UnidadeForm()
        return render(
            request,
            "accounts/unit_form.html",
            {"form": form, "action": "create", "page_title": "Criar Unidade"},
        )

    def post(self, request):
        form = UnidadeForm(request.POST)
        if form.is_valid():
            form.save()
            if request.htmx:
                from django_htmx.http import HttpResponseClientRedirect

                return HttpResponseClientRedirect(reverse("accounts:unit-list"))
            return redirect("accounts:unit-list")
        template = (
            "accounts/partials/unit_form.html"
            if request.htmx
            else "accounts/unit_form.html"
        )
        return render(request, template, {"form": form, "action": "create"})


class UnitUpdateView(AdminRequiredMixin, View):
    def get(self, request, pk):
        unit = get_object_or_404(UnidadeOrganizacional, pk=pk)
        form = UnidadeForm(instance=unit)
        return render(
            request,
            "accounts/unit_form.html",
            {
                "form": form,
                "action": "edit",
                "unit": unit,
                "page_title": "Editar Unidade",
            },
        )

    def post(self, request, pk):
        unit = get_object_or_404(UnidadeOrganizacional, pk=pk)
        form = UnidadeForm(request.POST, instance=unit)
        if form.is_valid():
            form.save()
            if request.htmx:
                from django_htmx.http import HttpResponseClientRedirect

                return HttpResponseClientRedirect(reverse("accounts:unit-list"))
            return redirect("accounts:unit-list")
        template = (
            "accounts/partials/unit_form.html"
            if request.htmx
            else "accounts/unit_form.html"
        )
        return render(
            request, template, {"form": form, "action": "edit", "unit": unit}
        )


class UnitDeactivateConfirmView(AdminRequiredMixin, View):
    def get(self, request, pk):
        unit = get_object_or_404(UnidadeOrganizacional, pk=pk)
        return render(
            request,
            "accounts/unit_confirm_deactivate.html",
            {"unit": unit},
        )


class UnitDeactivateView(AdminRequiredMixin, View):
    def post(self, request, pk):
        unit = get_object_or_404(UnidadeOrganizacional, pk=pk)
        unit.ativo = False
        unit.save()
        return render(
            request,
            "accounts/partials/unit_row.html",
            {"unit": unit},
        )
