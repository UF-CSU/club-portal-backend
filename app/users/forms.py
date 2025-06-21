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

    name = forms.CharField(
        label="name",
        widget=forms.TextInput(attrs={"class": "field-text", "placeholder": "Name"}),
        required=False,
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
        "name",
        "password",
        "confirm_password",
        "club",
        "event",
    ]
