# Generated by Django 4.2.20 on 2025-04-06 00:00

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0013_remove_profile_address_1_remove_profile_address_2_and_more"),
    ]

    operations = [
        migrations.RenameField(
            model_name="profile",
            old_name="title",
            new_name="prefix",
        ),
        migrations.AlterField(
            model_name="socialprofile",
            name="social_type",
            field=models.CharField(
                choices=[
                    ("discord", "Discord"),
                    ("instagram", "Instagram"),
                    ("facebook", "Facebook"),
                    ("twitter", "Twitter (X)"),
                    ("linkedin", "LinkedIn"),
                    ("github", "GitHub"),
                    ("website", "Personal Website"),
                    ("bluesky", "BlueSky"),
                    ("other", "Other"),
                ]
            ),
        ),
    ]
