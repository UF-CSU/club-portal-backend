from django.db.models.signals import post_save
from django.dispatch import receiver

from clubs.consts import INITIAL_CLUB_ROLES, INITIAL_TEAM_ROLES
from clubs.models import Club, ClubFile, ClubRole, Team, TeamRole
from utils.files import get_file_from_path
from utils.images import create_default_icon


@receiver(post_save, sender=Club)
def on_save_club(sender, instance: Club, created=False, **kwargs):
    """Automations to run when a club is created."""

    if instance.logo is None:
        initials = instance.alias or instance.name[0]
        logo_path = create_default_icon(
            initials, image_path="clubs/images/generated/", fileprefix=instance.pk
        )
        logo = ClubFile.objects.create(
            club=instance, file=get_file_from_path(logo_path)
        )

        instance.logo = logo
        instance.save()

    if not created:  # Skip if being updated
        return

    # Create roles after club creation
    for role in INITIAL_CLUB_ROLES:
        ClubRole.objects.create(
            club=instance,
            name=role["name"],
            default=role["default"],
            perm_labels=role["permissions"],
        )


@receiver(post_save, sender=Team)
def on_save_team(sender, instance: Team, created=False, **kwargs):
    """Automations to run when a team is created."""

    if not created:
        return

    for role in INITIAL_TEAM_ROLES:
        TeamRole.objects.create(
            team=instance,
            name=role["name"],
            default=role["default"],
            perm_labels=role["permissions"],
        )
