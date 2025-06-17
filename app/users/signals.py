import random

from django.db.models.signals import post_save
from django.dispatch import receiver
from PIL import Image, ImageDraw

from users.models import Profile, User
from utils.files import get_media_path
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

    colors = [
        "#1A73E8",  # (Blue)
        "#34A853",  # (Green)
        "#EA4335",  # (Red)
        "#F9AB00",  # (Amber)
        "#8E24AA",  # (Purple)
        "#00ACC1",  # (Teal)
        "#FF7043",  # (Coral)
        "#3949AB",  # (Indigo)
        "#43A047",  # (Dark Green)
        "#D81B60",  # (Pink)
    ]

    color = random.choice(colors)

    img = Image.new("RGB", (300, 300), color=color)
    draw = ImageDraw.Draw(img)

    initials = ""
    if instance.profile.first_name is not None and len(instance.profile.first_name) > 0:
        initials += instance.first_name[0]

    if instance.profile.last_name is not None and len(instance.profile.last_name) > 0:
        initials += instance.last_name[0]

    if initials == "":
        initials = instance.email[0]

    draw.text((150, 150), initials, fill="white", font_size=150, anchor="mm")

    path = get_media_path(
        "users/images/generated/", fileprefix=instance.id, fileext="png"
    )
    img.save(path)

    save_file_to_model(instance.profile, path, field="image")
