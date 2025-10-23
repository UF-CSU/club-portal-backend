import os

from django.contrib.auth import get_user_model
from django.core.management import BaseCommand
from django.db import transaction


class Command(BaseCommand):
    """Create an initial super user."""

    def handle(self, *args, **options):
        """Entrypoint for command"""

        # FIXME: Re-add this check after first deployment
        # if not bool(int(os.environ.get("DJANGO_DEBUG", 0))):
        #     self.stdout.write(
        #         self.style.ERROR(
        #             "Unable to automate super user creation when not in DEBUG mode."
        #         )
        #     )

        #     return
        email = os.environ.get("DJANGO_SUPERUSER_EMAIL")
        password = os.environ.get("DJANGO_SUPERUSER_PASS")

        User = get_user_model()
        super_users = User.objects.filter(is_superuser=True)
        existing_user = User.objects.filter(email=email)

        if not super_users.exists() and not existing_user.exists():
            with transaction.atomic():
                User.objects.create_superuser(email=email, password=password)

            self.stdout.write(
                self.style.SUCCESS(
                    f"Created super user with email {email} and password {password}."
                )
            )
        elif existing_user.exists() and not super_users.exists():
            self.stdout.write(
                self.style.WARNING(
                    f"Cannot create super user, a user with email {email} already exists"
                )
            )
