import os

from django.contrib.auth import get_user_model
from django.core.management import BaseCommand


class Command(BaseCommand):
    """Create an initial super user."""

    def handle(self, *args, **options):
        """Entrypoint for command"""

        if not bool(int(os.environ.get("DJANGO_DEBUG", 0))):
            self.stdout.write(
                self.style.ERROR(
                    "Unable to automate super user creation when not in DEBUG mode."
                )
            )

            return

        User = get_user_model()
        super_users = User.objects.filter(is_superuser=True)

        if not super_users.exists():
            email = os.environ.get("DJANGO_SUPERUSER_EMAIL")
            password = os.environ.get("DJANGO_SUPERUSER_PASS")
            User.objects.create_superuser(email=email, password=password)

            self.stdout.write(
                self.style.SUCCESS(
                    f"Created super user with email {email} and password {password}."
                )
            )
