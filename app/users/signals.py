from django.db.models.signals import post_save
from django.dispatch import receiver

from users.models import Profile, User
from utils.images import create_default_icon
from utils.models import save_file_to_model


@receiver(post_save, sender=User)
def on_save_user(sender, instance: User, created=False, **kwargs):
    """Runs when user object is saved."""

    if created:  # Skip if being created
        return
    elif not Profile.objects.filter(user=instance).exists():
        Profile.objects.create(user=instance)
        instance.refresh_from_db()

    # Skip if has image
    if instance.profile.image:
        return

    initials = ""
    if instance.profile.name is not None and len(instance.profile.name) > 0:
        initials = "".join([word[0] for word in instance.profile.name.split(" ", 3)])
    else:
        initials = instance.email[0]

    path = create_default_icon(
        initials, image_path="users/images/generated/", fileprefix=instance.pk
    )

    save_file_to_model(instance.profile, path, field="image")
