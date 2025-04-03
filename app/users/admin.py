"""
Users admin config.
"""

from django import forms
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.forms import UserChangeForm, UserCreationForm

from clubs.models import ClubMembership
from core.abstracts.admin import ModelAdminBase
from users.models import Profile, SocialProfile, User
from users.serializers import UserCsvSerializer


class UserProfileInline(admin.StackedInline):
    """User profile inline."""

    model = Profile
    can_delete = False
    verbose_name_plural = "profile"


class UserClubMembershipInline(admin.StackedInline):
    """Manage user memberships to a club in admin."""

    model = ClubMembership
    extra = 0


class UpdateUserForm(UserChangeForm):
    """Update user."""

    class Meta:
        fields = ("email",)


class CreateUserForm(UserCreationForm):
    """Create user."""

    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = UserCreationForm.Meta.fields + ("email",)


class SocialProfileInline(admin.StackedInline):
    """Manage user's social profiles in admin."""

    model = SocialProfile
    extra = 1


class UserAdmin(BaseUserAdmin, ModelAdminBase):
    """Manager users in admin dashbaord."""

    csv_serializer_class = UserCsvSerializer

    readonly_fields = (
        *BaseUserAdmin.readonly_fields,
        "date_joined",
    )

    fieldsets = (
        (None, {"fields": ("username", "email", "password")}),
        (
            "Permissions",
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                )
            },
        ),
        ("Important dates", {"fields": ("last_login", "date_joined")}),
    )

    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("email", "username", "password1", "password2"),
            },
        ),
    )

    inlines = (UserProfileInline, SocialProfileInline, UserClubMembershipInline)


admin.site.register(User, UserAdmin)
