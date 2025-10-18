from channels.routing import URLRouter
from channels.security.websocket import AllowedHostsOriginValidator

from core.middleware import WebSocketMiddlewareStack
from polls.routing import websocket_urlpatterns as polls_ws

websocket_urlpatterns = [
    *polls_ws,
]

application = AllowedHostsOriginValidator(
    WebSocketMiddlewareStack(URLRouter(websocket_urlpatterns))
)
