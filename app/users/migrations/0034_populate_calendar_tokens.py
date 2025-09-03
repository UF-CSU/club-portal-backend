# Generated migration to populate calendar_tokens for existing users

import uuid
from django.db import migrations


def populate_calendar_tokens(apps, schema_editor):
    """Ensure all users have a calendar_token."""
    User = apps.get_model("users", "User")
    
    # Update users that have NULL or empty calendar_token
    for user in User.objects.filter(calendar_token__isnull=True):
        user.calendar_token = uuid.uuid4()
        user.save(update_fields=['calendar_token'])


def reverse_populate_calendar_tokens(apps, schema_editor):
    """Reverse migration - set all calendar_tokens to NULL."""
    User = apps.get_model("users", "User")
    User.objects.update(calendar_token=None)


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0033_user_calendar_token"),
    ]

    operations = [
        migrations.RunPython(
            populate_calendar_tokens,
            reverse_populate_calendar_tokens,
        ),
    ]
