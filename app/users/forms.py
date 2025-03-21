from django import forms

from clubs.models import Club
from events.models import Event


class AuthForm(forms.Form):
    """Base fields for all auth forms."""

    password = forms.CharField(
        label="password",
        widget=forms.PasswordInput(
            attrs={"class": "field-text", "placeholder": "Password"}
        ),
    )
    event = forms.ModelChoiceField(
        label="event",
        widget=forms.HiddenInput(),
        queryset=Event.objects.all(),
        required=False,
    )
    club = forms.ModelChoiceField(
        label="club",
        widget=forms.HiddenInput(),
        queryset=Club.objects.all(),
        required=False,
    )


class LoginForm(AuthForm):
    """Allow members to authenticate with the club system."""

    username = forms.CharField(
        label="username",
        help_text="Username or Email",
        widget=forms.TextInput(
            attrs={"class": "field-text", "placeholder": "Username"}
        ),
    )

    field_order = ["username", "password", "event", "club"]


class RegisterForm(AuthForm):
    """New members can create accounts with the system."""

    first_name = forms.CharField(
        label="first_name",
        widget=forms.TextInput(
            attrs={"class": "field-text", "placeholder": "First Name"}
        ),
    )
    last_name = forms.CharField(
        label="last_name",
        widget=forms.TextInput(
            attrs={"class": "field-text", "placeholder": "Last Name"}
        ),
    )
    email = forms.EmailField(
        label="email",
        widget=forms.TextInput(attrs={"class": "field-text", "placeholder": "Email"}),
    )

    confirm_password = forms.CharField(
        label="confirm-password",
        widget=forms.PasswordInput(
            attrs={"class": "field-text", "placeholder": "Confirm Password"}
        ),
    )

    field_order = [
        "email",
        "first_name",
        "last_name",
        "password",
        "confirm_password",
        "club",
        "event",
    ]
