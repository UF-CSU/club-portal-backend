"""
Users admin config.
"""

from django import forms
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.forms import UserChangeForm, UserCreationForm

from clubs.models import ClubMembership
from core.abstracts.admin import ModelAdminBase
from users.defaults import DEFAULT_USER_PERMISSIONS
from users.models import Profile, SocialProfile, User, VerifiedEmail
from users.serializers import UserCsvSerializer
from users.services import UserService
from utils.formatting import plural_noun, plural_noun_display
from utils.permissions import parse_permissions


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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["password1"].required = False
        self.fields["password2"].required = False
        self.fields["password1"].widget.attrs["autocomplete"] = "off"
        self.fields["password2"].widget.attrs["autocomplete"] = "off"

    def clean_password2(self):
        password1 = self.cleaned_data.get("password1")
        password2 = self.cleaned_data.get("password2")
        if bool(password1) ^ bool(password2):
            raise forms.ValidationError("Fill out both fields")
        return password2

    def save(self, commit=True):
        user = super().save(commit=False)
        pwd = self.cleaned_data.get("password1")
        if pwd:
            user.set_password(pwd)
        else:
            # no password supplied -> make account non-loginable until a password is set
            user.set_unusable_password()
        if commit:
            user.save()
        return user

    class Meta:
        model = User
        fields = UserCreationForm.Meta.fields + ("email",)


class SocialProfileInline(admin.StackedInline):
    """Manage user's social profiles in admin."""

    model = SocialProfile
    extra = 1


class UserAdmin(BaseUserAdmin, ModelAdminBase):
    """Manager users in admin dashboard."""

    add_form = CreateUserForm

    csv_serializer_class = UserCsvSerializer

    list_display = ("username", "email", "name", "is_staff")
    search_fields = ("username", "name", "email")

    readonly_fields = (
        *BaseUserAdmin.readonly_fields,
        "date_joined",
        "profile_image",
        "is_onboarded",
    )
    actions = ("send_account_setup_link", "send_admin_setup_link", "sync_permissions")

    fieldsets = (
        (None, {"fields": ("username", "email", "password", "profile_image")}),
        (
            "Permissions",
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "is_onboarded",
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

    def profile_image(self, obj):
        return self.as_image(obj.profile.image)

    @admin.action
    def sync_permissions(self, request, queryset):
        """Sync permissions for selected users."""
        perms = parse_permissions(DEFAULT_USER_PERMISSIONS)

        for user in queryset:
            for perm in perms:
                if not user.user_permissions.filter(id=perm.id).exists():
                    user.user_permissions.add(perm)

        self.message_user(
            request,
            f"Successfully synced permissions for {plural_noun_display(queryset.count(), 'user')}",
        )

    @admin.action
    def send_account_setup_link(self, request, queryset):
        """Send password reset for each selected user."""

        for user in queryset:
            UserService(user).send_account_setup_link()

        self.message_user(
            request,
            f'Successfully sent setup link to {queryset.count()} {plural_noun(queryset.count(), "user")}',
        )

        return

    @admin.action
    def send_admin_setup_link(self, request, queryset):
        """Send link to setup admin account."""

        queryset.update(is_staff=True)

        for user in queryset:
            UserService(user).send_account_setup_link(send_to_client=False)

        self.message_user(
            request,
            f'Successfully sent admin setup link to {queryset.count()} {plural_noun(queryset.count(), "user")}',
        )

        return


admin.site.register(User, UserAdmin)
admin.site.register(VerifiedEmail)
