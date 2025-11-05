from django.core.cache import cache
from django.core.management import BaseCommand, CommandError

from utils.formatting import plural_noun_display


class Command(BaseCommand):
    """Manage cache via cli."""

    def add_arguments(self, parser):
        parser.add_argument("action", help="Clear cache")
        parser.add_argument("context", nargs="*")
        return super().add_arguments(parser)

    def handle(self, *args, **options):
        action = options.get("action", None)
        context = options.get("context", None)

        match action:
            case "clear":
                if not context:
                    cache.clear()
                    self.stdout.write(self.style.SUCCESS("Cleared full cache."))
                else:
                    keys = []
                    for key in context:
                        keys = [*keys, *cache.keys(f"*.{key}.*")]

                    if not keys:
                        self.stdout.write(self.style.SUCCESS("Removed 0 keys from cache."))
                    else:
                        cache.delete_many(keys=keys)
                        self.stdout.write(
                            self.style.SUCCESS(
                                f"Removed {plural_noun_display(keys, 'key')} from cache."
                            )
                        )

            case "keys":
                keys = []
                if not context:
                    keys = cache.keys("*")
                else:
                    for key in context:
                        keys = [*keys, *cache.keys(f"*.{key}.*")]

                if keys:
                    self.stdout.write(f"Keys ({len(keys)} total): \n\n{'\n'.join(keys)}")
                else:
                    self.stdout.write("0 keys found")
            case _:
                raise CommandError('Unknown action "%s"' % action)
