from django.db.models.signals import post_save
from django.dispatch import receiver

from clubs.consts import INITIAL_CLUB_ROLES
from clubs.models import Club, ClubRole


@receiver(post_save, sender=Club)
def on_save_club(sender, instance: Club, created=False, **kwargs):
    """Automations to run when a club is created."""

    if not created:
        # Only proceed if club is being created
        return

    # Create roles after club creation
    for role in INITIAL_CLUB_ROLES:
        ClubRole.objects.create(
            club=instance,
            name=role["name"],
            default=role["default"],
            perm_labels=role["permissions"],
        )
