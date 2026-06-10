"""
Accounts views: login, logout, password reset.
Admin panel user/unit CRUD views are in Plan 03.
"""
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.views import (
    PasswordResetConfirmView,
    PasswordResetDoneView,
    PasswordResetView,
)
from django.shortcuts import redirect, render


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
            from .models import User as UserModel

            username = request.POST.get("username", "")
            try:
                existing_user = UserModel.objects.get(email=username)
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
            except UserModel.DoesNotExist:
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
