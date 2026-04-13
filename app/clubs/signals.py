from app.settings import ENABLE_AUTO_CREATE_CLUB_LOGO
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver
from lib.celery import delay_task
from utils.images import create_default_icon

from clubs.defaults import INITIAL_CLUB_ROLES, INITIAL_TEAM_ROLES
from clubs.models import Club, ClubFile, ClubRole, ClubTag, Team, TeamRole
from clubs.tasks import regenerate_club_preview_cache_task


@receiver(post_save, sender=Club)
def on_save_club(sender, instance: Club, created=False, **kwargs):
    """Automations to run when a club is created."""

    if instance.logo is None and ENABLE_AUTO_CREATE_CLUB_LOGO:
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


@receiver([post_save, post_delete])
def refresh_preview_cache(sender, instance: Club | ClubTag, created=False, **kwargs):
    """Refreshes the club preview cache when clubs are changed"""

    if sender == Club:
        delay_task(
            regenerate_club_preview_cache_task,
            club_ids=[instance.id],
        )
    elif sender == ClubTag:
        delay_task(
            regenerate_club_preview_cache_task,
            club_ids=list(instance.clubs.all().values_list("id", flat=True)),
        )
