from django.core.management import BaseCommand

from core.typegen import SERIALIZERS_CREATE_READ_UPDATE, SERIALIZERS_READONLY
from lib.serializer_typegen import TypeGenerator

FILE_OUT = "generated/club-portal.d.ts"


class Command(BaseCommand):
    """Generate TypeScript types for Django models."""

    def handle(self, *args, **options):
        """Entrypoint for command."""

        tg = TypeGenerator(
            SERIALIZERS_CREATE_READ_UPDATE,
            readonly_serializer_classes=SERIALIZERS_READONLY,
        )
        tg.generate_docs(FILE_OUT)

        print(f"Generated {tg.types_generated} types in {FILE_OUT}")
