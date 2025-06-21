import logging

from django.core.management import BaseCommand

from clubs.serializers import ClubMembershipSerializer, ClubSerializer, TeamSerializer
from events.serializers import EventSerializer
from lib.serializer_typegen import TypeGenerator
from users.serializers import UserSerializer

FILE_OUT = "generated/club-portal.d.ts"


class Command(BaseCommand):
    """Generate TypeScript types for Django models."""

    def handle(self, *args, **options):
        """Entrypoint for command."""

        target_serializers = [
            ClubSerializer,
            ClubMembershipSerializer,
            TeamSerializer,
            EventSerializer,
            UserSerializer,
        ]

        tg = TypeGenerator(target_serializers)
        tg.generate_docs(FILE_OUT)

        logging.info(f"Generated {len(target_serializers)} types in {FILE_OUT}")
