from channels.routing import URLRouter
from channels.security.websocket import AllowedHostsOriginValidator

from core.middleware import WebSocketMiddleware
from polls.routing import websocket_urlpatterns as polls_ws

websocket_urlpatterns = [
    *polls_ws,
]

application = AllowedHostsOriginValidator(
    WebSocketMiddleware(URLRouter(websocket_urlpatterns))
)
