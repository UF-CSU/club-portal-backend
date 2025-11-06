from analytics.routing import websocket_urlpatterns as analytics_ws
from channels.routing import URLRouter
from channels.security.websocket import AllowedHostsOriginValidator
from core.middleware import WebSocketMiddleware
from polls.routing import websocket_urlpatterns as polls_ws
from querycsv.routing import websocket_urlpatterns as query_ws

websocket_urlpatterns = [
    *polls_ws,
    *query_ws,
    *analytics_ws,
]

application = AllowedHostsOriginValidator(
    WebSocketMiddleware(URLRouter(websocket_urlpatterns))
)
