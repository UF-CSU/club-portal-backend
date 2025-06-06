# Generated by Django 4.2.20 on 2025-03-13 14:03

import clubs.models
import django.core.validators
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("clubs", "0019_eventtag_event_tags"),
    ]

    operations = [
        migrations.CreateModel(
            name="ClubTag",
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
                (
                    "name",
                    models.CharField(
                        max_length=16,
                        validators=[django.core.validators.MinLengthValidator(2)],
                    ),
                ),
                (
                    "color",
                    models.CharField(
                        choices=[
                            ("red", "Red"),
                            ("orange", "Orange"),
                            ("yellow", "Yellow"),
                            ("green", "Green"),
                            ("blue", "Blue"),
                            ("purple", "Purple"),
                            ("grey", "Grey"),
                        ],
                        default="grey",
                    ),
                ),
                ("order", models.IntegerField(blank=True, default=0)),
            ],
            options={
                "ordering": ["order", "name"],
                "abstract": False,
            },
        ),
        migrations.AddField(
            model_name="club",
            name="about",
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="club",
            name="alias",
            field=models.CharField(blank=True, max_length=7, null=True, unique=True),
        ),
        migrations.AddField(
            model_name="club",
            name="contact_email",
            field=models.EmailField(blank=True, max_length=254, null=True),
        ),
        migrations.AddField(
            model_name="club",
            name="founding_year",
            field=models.IntegerField(
                default=clubs.models.get_default_founding_year,
                validators=[
                    django.core.validators.MinValueValidator(1900),
                    clubs.models.validate_max_founding_year,
                ],
            ),
        ),
        migrations.CreateModel(
            name="ClubSocialProfile",
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
                ("url", models.URLField()),
                ("username", models.CharField()),
                (
                    "social_type",
                    models.CharField(
                        choices=[
                            ("discord", "Discord"),
                            ("instagram", "Instagram"),
                            ("facebook", "Facebook"),
                            ("twitter", "Twitter (X)"),
                        ]
                    ),
                ),
                ("order", models.IntegerField(blank=True, default=0)),
                (
                    "club",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="socials",
                        to="clubs.club",
                    ),
                ),
            ],
            options={
                "ordering": ["order", "id"],
                "abstract": False,
            },
        ),
        migrations.AddField(
            model_name="club",
            name="tags",
            field=models.ManyToManyField(blank=True, to="clubs.clubtag"),
        ),
    ]
