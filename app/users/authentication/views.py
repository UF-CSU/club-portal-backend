from django.contrib.auth.views import (
    LoginView,
    LogoutView,
    PasswordChangeDoneView,
    PasswordChangeView,
    PasswordResetCompleteView,
    PasswordResetConfirmView,
    PasswordResetDoneView,
    PasswordResetView,
)
from django.urls import reverse_lazy

from app.settings import LOGIN_URL


class AuthLoginView(LoginView):
    """
    Wrap default login view.
    Extends FormView.
    """

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.fields["username"].widget.attrs.update({"class": "field-text"})
        form.fields["username"].widget.attrs.update({"placeholder": "Username"})
        form.fields["password"].widget.attrs.update({"class": "field-text"})
        form.fields["password"].widget.attrs.update({"placeholder": "Password"})
        return form

    redirect_authenticated_user = True
    template_name = "users/authentication/login_user.html"

    def get_context_data(self, **kwargs):
        kwargs["next"] = self.request.GET.get("next", None)
        return super().get_context_data(**kwargs)


class AuthLogoutView(LogoutView):
    """
    Wrap default logout view.
    Extends TemplateView.
    """

    next_page = LOGIN_URL


# Template for the Email sent to the user requesting the password reset
class AuthPassResetView(PasswordResetView):
    """
    Wrap default password reset view.
    Extends FormView.
    """

    extra_context = {"submit_button": "Reset Password"}
    success_url = reverse_lazy("users-auth:resetpassword_done")
    email_template_name = "users/authentication/reset_pass_email.html"
    template_name = "users/authentication/reset_pass_request_form.html"


class AuthPassResetDoneView(PasswordResetDoneView):
    """
    Wrap default password reset done view.
    Extends TemplateView.
    """

    template_name = "users/authentication/reset_pass_done.html"


class AuthPassResetConfirmView(PasswordResetConfirmView):
    """
    Wrap default password reset confirm view.
    Extends FormView.
    """

    extra_context = {"submit_button": "Confirm"}
    success_url = reverse_lazy("users-auth:resetpassword_complete")
    template_name = "users/authentication/reset_pass_confirm_form.html"


class AuthPassResetCompleteView(PasswordResetCompleteView):
    """
    Wrap default password reset complete view.
    Extends TemplateView.
    """

    template_name = "users/authentication/reset_pass_complete.html"


class AuthChangePasswordView(PasswordChangeView):
    """
    Wrap default change password view.
    Extends FormView.
    """

    extra_context = {"submit_button": "Change Password"}
    success_url = reverse_lazy("users-auth:changepassword_done")


class AuthPasswordChangeDoneView(PasswordChangeDoneView):
    """Wrap default password change done view."""

    template_name = "users/authentication/change_pass_done.html"
