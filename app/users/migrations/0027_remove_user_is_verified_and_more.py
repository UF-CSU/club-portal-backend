# Generated by Django 4.2.23 on 2025-06-22 19:46

from django.db import migrations, models
import users.models


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0026_emailverificationcode_verifiedemail"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="user",
            name="is_verified",
        ),
        migrations.AlterField(
            model_name="emailverificationcode",
            name="code",
            field=models.CharField(
                default=users.models.generate_verification_code,
                max_length=6,
                unique=True,
            ),
        ),
        migrations.AlterField(
            model_name="emailverificationcode",
            name="expires_at",
            field=models.DateTimeField(
                default=users.models.generate_verification_expiry, editable=False
            ),
        ),
    ]
