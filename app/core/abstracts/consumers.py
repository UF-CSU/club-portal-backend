from channels.generic.websocket import AsyncJsonWebsocketConsumer
from django.contrib.auth.models import AnonymousUser


# ---------- Consumer Permissions ----------
class ConsumerPermission:
    """
    A base class from which all consumer permission classes should inherit.
    """

    def has_permission(self, user):
        """
        Return `True` if permission is granted, `False` otherwise.
        """
        return True


class ConsumerAllowAny(ConsumerPermission):
    """
    Allow any access.
    This isn't strictly required, since you could use an empty
    permission_classes list, but it's useful because it makes the intention
    more explicit.
    """

    def has_permission(self, user):
        return True


class ConsumerIsAuthenticated(ConsumerPermission):
    """
    Allows access only to authenticated users.
    """

    def has_permission(self, user):
        return bool(user and user.is_authenticated)


# ---------- Base Consumer ----------
class ConsumerBase(AsyncJsonWebsocketConsumer):
    """
    Provide core functionality, additional type hints, and improved documentaton for consumers.
    """

    permission_classes = [ConsumerIsAuthenticated]
    """Determines what a user can do."""

    group_name = None
    channel_name = None

    async def connect(self):
        """
        Called when a client tries to connect.
        Checks permissions and closes connection if not allowed.
        """
        if not self.has_permission():
            await self.close(code=3000)  # 401 equivalent for WebSockets
            return False

        subprotocols = self.scope["subprotocols"]
        if "Authorization" in subprotocols:
            await self.accept("Authorization")
        else:
            await self.accept()
        return True

    async def disconnect(self, _close_code):
        if not self.group_name or not self.channel_name:
            return
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    def has_permission(self) -> bool:
        """
        Check if the current user passes all permissions.
        """
        user = self.scope.get("user", AnonymousUser())

        for perm_class in self.permission_classes:
            perm = perm_class()
            allowed = perm.has_permission(user)

            if not allowed:
                return False

        return True
