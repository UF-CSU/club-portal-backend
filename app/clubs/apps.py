from django.apps import AppConfig
from lib.emails import send_html_mail


class ClubConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "clubs"

    def ready(self) -> None:
        from . import signals  # noqa: F401

        send_html_mail(
            "Test email", ["user@example.com"], html_template="test-email.html"
        )

        return super().ready() 
