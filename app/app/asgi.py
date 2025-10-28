"""
ASGI config for app project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/4.2/howto/deployment/asgi/
"""

import os

from channels.routing import ProtocolTypeRouter
from django.core.asgi import get_asgi_application
from uvicorn.workers import UvicornWorker


class DjangoUvicornWorker(UvicornWorker):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.config.lifespan = "off"


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "app.settings")


django_application = get_asgi_application()

from .routing import application as ws_application  # noqa: E402

application = ProtocolTypeRouter(
    {"http": django_application, "websocket": ws_application}
)
