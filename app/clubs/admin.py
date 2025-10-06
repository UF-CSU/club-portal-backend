from typing import Optional

from django import forms
from django.contrib import admin

from clubs.forms import TeamMembershipForm
from clubs.models import (
    Club,
    ClubApiKey,
    ClubFile,
    ClubMembership,
    ClubPhoto,
    ClubRole,
    ClubSocialProfile,
    ClubTag,
    RoleType,
    Team,
    TeamMembership,
    TeamRole,
)
from clubs.serializers import (
    ClubCsvSerializer,
    ClubMembershipCsvSerializer,
    ClubRoleCsvSerializer,
    TeamCsvSerializer,
)
from core.abstracts.admin import ModelAdminBase
from utils.formatting import plural_noun


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
            formset.form.base_fields["roles"].queryset = roles_qs.filter(club__id=obj.id)
        except Exception as e:
            print("Unable to override membership field in admin:", e)

        return formset


class ClubPhotoInlineAdmin(admin.TabularInline):
    """Manage club carousel photos in admin."""

    model = ClubPhoto
    extra = 0


class ClubSocialInlineAdmin(admin.TabularInline):
    """Manage links to club social media in admin."""

    model = ClubSocialProfile
    extra = 0


class ClubRoleInlineAdmin(admin.TabularInline):
    """Manage roles for a club."""

    model = ClubRole
    extra = 0
    exclude = ["permissions"]


class ClubAdmin(ModelAdminBase):
    """Admin config for Clubs."""

    csv_serializer_class = ClubCsvSerializer

    inlines = (
        ClubSocialInlineAdmin,
        ClubPhotoInlineAdmin,
        ClubRoleInlineAdmin,
    )
    filter_horizontal = (
        "tags",
        "majors",
    )
    list_display = (
        "name",
        "alias",
        "id",
        "members_count",
        "created_at",
    )
    search_fields = (
        "name",
        "alias",
    )
    list_filter = (
        "tags",
        "majors",
    )

    def members_count(self, obj):
        return obj.memberships.count()


class ClubRoleForm(forms.ModelForm):
    """Defines how roles should be edited."""

    class Meta:
        model = ClubRole
        fields = "__all__"

    def clean(self):
        super().clean()

        # Prevent manual setting of permissions if there is a permissions preset
        if self.cleaned_data.get("role_type", RoleType.CUSTOM) != RoleType.CUSTOM:
            self.cleaned_data.pop("permissions")


class ClubRoleAdmin(ModelAdminBase):
    """Manage club roles in admin."""

    csv_serializer_class = ClubRoleCsvSerializer
    form = ClubRoleForm

    list_display = ("name", "club", "role_type", "is_default", "is_executive", "order")
    prefetch_related_fields = ("permissions",)
    search_fields = (
        "name",
        "club__name",
        "club__alias",
    )
    actions = ("sync_roles",)

    @admin.action
    def sync_roles(self, request, queryset):
        """Sync role permissions."""

        queryset.update(cached_role_type=None)
        for role in queryset:
            role.save()

        self.message_user(
            request,
            message=f"Synced {queryset.count()} {plural_noun(queryset.count(), 'role')}",
        )

        return


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
    search_fields = (
        "user__email",
        "user__profile__name",
        "user__id",
        "club__name",
        "club__alias",
    )

    autocomplete_fields = (
        "club",
        "user",
    )
    filter_horizontal = ("roles",)

    def get_exclude(self, request, obj=None):
        excluded = super().get_exclude(request, obj) or []

        if obj is None:
            return excluded + ["roles"]

        return excluded

    def formfield_for_manytomany(self, db_field, request, **kwargs):
        if db_field.name == "roles" and "object_id" in request.resolver_match.kwargs:
            membership_id = request.resolver_match.kwargs["object_id"]
            club = ClubMembership.objects.get(id=membership_id).club
            kwargs["queryset"] = ClubRole.objects.filter(club=club)
        return super().formfield_for_manytomany(db_field, request, **kwargs)

    def club_roles(self, obj):
        return ", ".join(role.name for role in list(obj.roles.all()))


class TeamMembershipInlineAdmin(admin.TabularInline):
    """Manage user assignments to a team."""

    model = TeamMembership
    extra = 0
    form = TeamMembershipForm
    fields = ("user", "roles", "order", "order_override")
    readonly_fields = ("order",)

    def get_formset(self, request, obj=None, **kwargs):
        if obj:
            self.form.parent_model = obj
        formset = super().get_formset(request, obj, **kwargs)

        # Restrict roles to ones owned by club
        try:
            roles_qs = formset.form.base_fields["roles"].queryset
            formset.form.base_fields["roles"].queryset = roles_qs.filter(team__id=obj.id)
        except Exception as e:
            print("Unable to override membership field in admin:", e)

        return formset


class TeamRoleInlineAdmin(admin.TabularInline):
    """Manage team roles in admin."""

    model = TeamRole
    extra = 0
    exclude = ("permissions",)


class TeamAdmin(ModelAdminBase):
    """Manage club teams in admin dashboard."""

    csv_serializer_class = TeamCsvSerializer

    list_display = ("__str__", "club", "members_count")
    inlines = (
        TeamRoleInlineAdmin,
        TeamMembershipInlineAdmin,
    )

    select_related_fields = ("club",)
    prefetch_related_fields = ("memberships", "memberships__user", "memberships__roles")

    def members_count(self, obj):
        return obj.memberships.count()


class TeamRoleAdmin(ModelAdminBase):
    """Manage team roles in admin."""

    list_display = (
        "name",
        "team",
        "club",
        "order",
    )
    filter_horizontal = ("permissions",)
    list_filter = ("team",)
    search_fields = (
        "name",
        "team__name",
        "team__club__name",
        "team__club__alias",
    )
    prefetch_related_fields = ("permissions",)


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

    filter_horizontal = ("permissions",)


admin.site.register(Club, ClubAdmin)
admin.site.register(ClubRole, ClubRoleAdmin)
admin.site.register(ClubTag, ClubTagAdmin)
admin.site.register(Team, TeamAdmin)
admin.site.register(TeamRole, TeamRoleAdmin)
admin.site.register(ClubMembership, ClubMembershipAdmin)
admin.site.register(ClubApiKey, ApiKeyAdmin)
admin.site.register(ClubFile)
