from django.apps import AppConfig


class ClubConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "clubs"

    def ready(self) -> None:
        from . import signals  # noqa: F401

        return super().ready()
