from django.db.models.signals import post_save
from django.dispatch import receiver
from utils.images import create_default_icon
from utils.permissions import parse_permissions

from clubs.defaults import (
    ADMIN_ROLE_PERMISSIONS,
    INITIAL_CLUB_ROLES,
    INITIAL_TEAM_ROLES,
    VIEWER_ROLE_PERMISSIONS,
)
from clubs.models import Club, ClubFile, ClubRole, RoleType, Team, TeamRole


@receiver(post_save, sender=Club)
def on_save_club(sender, instance: Club, created=False, **kwargs):
    """Automations to run when a club is created."""

    if instance.logo is None:
        initials = instance.alias or instance.name[0]
        logo = create_default_icon(
            initials, image_path="clubs/images/generated/", fileprefix=instance.pk
        )
        logo = ClubFile.objects.create(club=instance, file=logo)

        instance.logo = logo
        instance.save()

    if not created:  # Only continue if being created
        return

    # Create roles after club creation
    for role in INITIAL_CLUB_ROLES:
        ClubRole.objects.create(
            club=instance,
            name=role["name"],
            role_type=role["role_type"],
            is_default=role["is_default"],
            is_executive=role["is_executive"],
            is_official=role["is_official"],
            is_voter=role["is_voter"],
        )


@receiver(post_save, sender=Team)
def on_save_team(sender, instance: Team, created=False, **kwargs):
    """Automations to run when a team is created."""

    if not created:  # Only continue if being created
        return

    for role in INITIAL_TEAM_ROLES:
        TeamRole.objects.create(
            team=instance,
            name=role["name"],
            role_type=role["role_type"],
            is_default=role["is_default"],
        )


@receiver(post_save, sender=ClubRole)
def on_save_club_role(sender, instance: ClubRole, created=False, **kwargs):
    """
    When saving roles, sync permissions for role type.

    Ex: When setting role to VIEWER, set permissions as viewer permissions.
    """

    if created:  # Only continue if being updated
        return

    if instance.role_type == RoleType.CUSTOM:
        # Skip if role type is set to custom
        if instance.cached_role_type != RoleType.CUSTOM:
            instance.cached_role_type = RoleType.CUSTOM
            instance.save()
        return

    elif instance.role_type == RoleType.VIEWER:
        if instance.cached_role_type != RoleType.VIEWER:
            # Role type out of sync, set permissions
            instance.cached_role_type = RoleType.VIEWER
            instance.permissions.set(parse_permissions(VIEWER_ROLE_PERMISSIONS))
            instance.save()
        elif instance.perm_labels != VIEWER_ROLE_PERMISSIONS:
            # Role type in sync, permissions out of sync
            instance.role_type = RoleType.CUSTOM
            instance.cached_role_type = RoleType.CUSTOM
            instance.save()
        else:
            # Role type in sync, permissions in sync
            pass
    elif instance.role_type == RoleType.ADMIN:
        if instance.cached_role_type != RoleType.ADMIN:
            # Role type out of sync, set permissions
            instance.cached_role_type = RoleType.ADMIN
            instance.permissions.set(parse_permissions(ADMIN_ROLE_PERMISSIONS))
            instance.save()
        elif instance.perm_labels != ADMIN_ROLE_PERMISSIONS:
            # Role type in sync, permissions out of sync
            instance.role_type = RoleType.CUSTOM
            instance.cached_role_type = RoleType.CUSTOM
            instance.save()
        else:
            # Role type in sync, permissions in sync
            pass
    else:
        # Unknown role type
        pass
