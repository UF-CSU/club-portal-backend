from django.db.models.signals import post_save
from django.dispatch import receiver

from app.settings import SCHOOL_EMAIL_DOMAIN
from users.defaults import DEFAULT_USER_PERMISSIONS
from users.models import Profile, User
from utils.images import create_default_icon
from utils.models import save_file_to_model
from utils.permissions import parse_permissions


# @receiver(pre_save, sender=User)
# def pre_save_user(sender, instance: User, created=False, **kwargs):
#     """Runs before saving a user to database."""

#     # Set initial cached email value
#     if created:
#         instance.cached_email = instance.email
#         return

#     # Set cached email value, optionally change email if applicable
#     if instance.email != instance.cached_email:
#         if instance.username == instance.cached_email:
#             instance.username = instance.email

#         instance.cached_email = instance.email


@receiver(post_save, sender=User)
def on_save_user(sender, instance: User, created=False, **kwargs):
    """Runs when user object is saved."""

    # Set default permissions for all users
    if instance.user_permissions.all().count() == 0:
        instance.user_permissions.set(parse_permissions(DEFAULT_USER_PERMISSIONS))

    # Skip if being created
    if created:
        return

    if not Profile.objects.filter(user=instance).exists():
        Profile.objects.create(user=instance)
        instance.refresh_from_db()

    if instance.profile.school_email is None and instance.email.endswith(
        SCHOOL_EMAIL_DOMAIN
    ):
        instance.profile.school_email = instance.email
        instance.profile.save()

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
