from django.core.management import BaseCommand

from core.typegen import SERIALIZERS_CREATE_READ_UPDATE, SERIALIZERS_READONLY
from lib.serializer_typegen import TypeGenerator

FILE_OUT = "generated/"


class Command(BaseCommand):
    """Generate TypeScript types for Django models."""

    def add_arguments(self, parser):
        parser.add_argument(
            "--check",
            action="store_true",
            help="Do not generate types file, just parse types.",
        )
        return super().add_arguments(parser)

    def handle(self, *args, **options):
        """Entrypoint for command."""

        write_types = not options.get("check", False)

        tg = TypeGenerator(
            SERIALIZERS_CREATE_READ_UPDATE,
            readonly_serializer_classes=SERIALIZERS_READONLY,
        )
        tg.generate_docs(FILE_OUT, write_types=write_types)

        print(f"Generated {tg.types_generated} types in {FILE_OUT}")
