from django.conf import settings
from django.contrib import messages
from django.contrib.auth import views
from django.contrib.auth.decorators import login_not_required
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.views.generic import CreateView

from heuriva.apps.accounts.forms import UserCreationForm


def registration_required(view_func):
    """Decorator to check if registration is enabled."""

    def wrapper(request, *args, **kwargs):
        if not getattr(settings, "REGISTRATION_ENABLED", True):
            return HttpResponse(
                "<h1>Registros Temporariamente Desabilitados</h1>"
                "<p>Estamos em fase de preparação. Em breve você poderá criar sua conta!</p>",
                status=403,
            )
        return view_func(request, *args, **kwargs)

    return wrapper


@method_decorator(login_not_required, name="dispatch")
@method_decorator(registration_required, name="dispatch")
class SignUpView(CreateView):
    form_class = UserCreationForm
    success_url = reverse_lazy("accounts:login")
    template_name = "accounts/signup.html"


@method_decorator(registration_required, name="dispatch")
class LoginView(views.LoginView):
    template_name = "accounts/login.html"
    redirect_authenticated_user = True


class LogoutView(views.LogoutView):
    pass


class PasswordChangeView(views.PasswordChangeView):
    template_name = "accounts/password_change_form.html"
    success_url = reverse_lazy("accounts:password_change_done")


class PasswordChangeDoneView(views.PasswordChangeDoneView):
    template_name = "accounts/password_change_done.html"


class PasswordResetView(views.PasswordResetView):
    template_name = "accounts/password_reset_form.html"
    email_template_name = "accounts/password_reset_email.html"
    success_url = reverse_lazy("accounts:password_reset_done")


class PasswordResetDoneView(views.PasswordResetDoneView):
    template_name = "accounts/password_reset_done.html"


class PasswordResetConfirmView(views.PasswordResetConfirmView):
    template_name = "accounts/password_reset_confirm.html"
    success_url = reverse_lazy("accounts:password_reset_complete")


class PasswordResetCompleteView(views.PasswordResetCompleteView):
    template_name = "accounts/password_reset_complete.html"


def profile_view(request):
    """Display user profile."""
    return render(request, "accounts/profile.html")


def profile_update(request):
    """Update user profile information."""
    if request.method == "POST":
        first_name = request.POST.get("first_name", "")
        last_name = request.POST.get("last_name", "")

        request.user.first_name = first_name
        request.user.last_name = last_name
        request.user.save()

        messages.success(request, "Perfil atualizado com sucesso!")
        return redirect("accounts:profile")

    return redirect("accounts:profile")


def email_change(request):
    """Change user email."""
    if request.method == "POST":
        new_email = request.POST.get("email")

        if new_email and new_email != request.user.email:
            # Check if email is already in use
            from .models import User

            if User.objects.filter(email=new_email).exists():
                messages.error(request, "Este e-mail já está em uso.")
            else:
                request.user.email = new_email
                request.user.save()
                messages.success(request, "E-mail alterado com sucesso!")

        return redirect("accounts:profile")

    return redirect("accounts:profile")


def delete_account(request):
    """Delete user account."""
    if request.method == "POST":
        user = request.user
        user.delete()
        messages.success(request, "Conta excluída com sucesso.")
        return redirect("pages:index")

    return redirect("accounts:profile")
