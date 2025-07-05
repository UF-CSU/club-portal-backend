from typing import Optional

from django.contrib import admin

from clubs.forms import TeamMembershipForm
from clubs.models import (
    Club,
    ClubApiKey,
    ClubMembership,
    ClubPhoto,
    ClubRole,
    ClubSocialProfile,
    ClubTag,
    Team,
    TeamMembership,
    TeamRole,
)
from clubs.serializers import (
    ClubCsvSerializer,
    ClubMembershipCsvSerializer,
    TeamCsvSerializer,
)
from core.abstracts.admin import ModelAdminBase


class ClubMembershipInlineAdmin(admin.StackedInline):
    """Create club memberships in admin."""

    model = ClubMembership
    extra = 0

    def get_formset(self, request, obj: Optional[Club] = None, **kwargs):
        """Override default formset."""
        formset = super().get_formset(request, obj, **kwargs)

        # Restrict roles to ones owned by club
        try:
            roles_qs = formset.form.base_fields["roles"].queryset
            formset.form.base_fields["roles"].queryset = roles_qs.filter(
                club__id=obj.id
            )
        except Exception as e:
            print("Unable to override membership field in admin:", e)

        return formset


class ClubRoleInlineAdmin(admin.StackedInline):
    """Manage club roles in admin."""

    model = ClubRole
    extra = 0


class ClubPhotoInlineAdmin(admin.TabularInline):
    """Manage club carousel photos in admin."""

    model = ClubPhoto
    extra = 0


class ClubSocialInlineAdmin(admin.TabularInline):
    """Manage links to club social media in admin."""

    model = ClubSocialProfile
    extra = 0


class ClubAdmin(ModelAdminBase):
    """Admin config for Clubs."""

    csv_serializer_class = ClubCsvSerializer

    inlines = (
        ClubRoleInlineAdmin,
        ClubMembershipInlineAdmin,
        ClubSocialInlineAdmin,
        ClubPhotoInlineAdmin,
    )
    filter_horizontal = ("tags",)
    list_display = (
        "name",
        "alias",
        "id",
        "members_count",
        "created_at",
    )

    def members_count(self, obj):
        return obj.memberships.count()


class ClubTagAdmin(ModelAdminBase):
    """Manage club tags in admin dashboard."""


class ClubMembershipAdmin(ModelAdminBase):
    """Manage club memberships in admin."""

    csv_serializer_class = ClubMembershipCsvSerializer

    list_display = (
        "__str__",
        "club",
        "club_roles",
        "created_at",
    )

    def club_roles(self, obj):
        return ", ".join(str(role) for role in list(obj.roles.all()))


class TeamMembershipInlineAdmin(admin.TabularInline):
    """Manage user assignments to a team."""

    model = TeamMembership
    extra = 1
    form = TeamMembershipForm

    def get_formset(self, request, obj=None, **kwargs):
        if obj:
            self.form.parent_model = obj
        formset = super().get_formset(request, obj, **kwargs)

        # Restrict roles to ones owned by club
        try:
            roles_qs = formset.form.base_fields["roles"].queryset
            formset.form.base_fields["roles"].queryset = roles_qs.filter(
                team__id=obj.id
            )
        except Exception as e:
            print("Unable to override membership field in admin:", e)

        return formset


class TeamRoleInlineAdmin(admin.StackedInline):
    """Manage team roles in admin."""

    model = TeamRole
    extra = 0


class TeamAdmin(ModelAdminBase):
    """Manage club teams in admin dashboard."""

    csv_serializer_class = TeamCsvSerializer

    list_display = ("__str__", "club", "points", "members_count")
    inlines = (
        TeamRoleInlineAdmin,
        TeamMembershipInlineAdmin,
    )

    def members_count(self, obj):
        return obj.memberships.count()


class ApiKeyAdmin(ModelAdminBase):
    """Manage API Keys in admin."""

    readonly_fields = (
        "user_agent",
        "secret",
    )

    list_display = (
        "__str__",
        "id",
        "club",
        "created_at",
    )


admin.site.register(Club, ClubAdmin)
admin.site.register(ClubTag, ClubTagAdmin)
admin.site.register(Team, TeamAdmin)
admin.site.register(ClubMembership, ClubMembershipAdmin)
admin.site.register(ClubSocialProfile)
admin.site.register(ClubPhoto)
admin.site.register(ClubApiKey, ApiKeyAdmin)
