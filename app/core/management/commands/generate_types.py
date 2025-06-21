import logging

from django.core.management import BaseCommand

from events.serializers import EventSerializer
from lib.ts_generator import TypeGenerator

FILE_OUT = "generated/club-portal.d.ts"


class Command(BaseCommand):
    """Generate TypeScript types for Django models."""

    def handle(self, *args, **options):
        """Entrypoint for command."""
        from clubs.serializers import ClubSerializer
        from users.serializers import UserSerializer

        target_serializers = [ClubSerializer, UserSerializer, EventSerializer]

        tg = TypeGenerator(target_serializers)
        tg.generate_docs(FILE_OUT)

        logging.info(f"Generated {len(target_serializers)} types in {FILE_OUT}")
