# Generated by Django 4.2.23 on 2025-06-23 00:08

from django.db import migrations, models
import django.db.models.deletion
import utils.models


class Migration(migrations.Migration):

    dependencies = [
        ("clubs", "0033_clubmembership_is_admin"),
    ]

    operations = [
        migrations.AddField(
            model_name="club",
            name="banner",
            field=models.ImageField(
                blank=True,
                null=True,
                upload_to=utils.models.UploadFilepathFactory("clubs/banners/"),
            ),
        ),
        migrations.CreateModel(
            name="ClubPhoto",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("photo", models.ImageField(upload_to="club_photos/")),
                ("order", models.PositiveIntegerField(default=0)),
                (
                    "club",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="photos",
                        to="clubs.club",
                    ),
                ),
            ],
        ),
        migrations.AddConstraint(
            model_name="clubphoto",
            constraint=models.UniqueConstraint(
                fields=("order", "club"), name="unique_order_per_club"
            ),
        ),
    ]
