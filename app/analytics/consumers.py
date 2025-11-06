from asgiref.sync import sync_to_async
from core.abstracts.consumers import ConsumerBase

from analytics.models import Link


class LinkVisitConsumer(ConsumerBase):
    """Send update when there's a new link visit."""

    # permission_classes = []

    async def _get_link_visit_count(self):
        """Get visit count for link."""

        link_id = self.scope["url_route"]["kwargs"]["link_id"]

        link = await Link.objects.aget(id=link_id)

        def _visit_count():
            return link.visit_count

        count = await sync_to_async(_visit_count)()
        return count

    async def connect(self):
        connected = await super().connect()
        if not connected:
            return

        link_id = self.scope["url_route"]["kwargs"]["link_id"]
        self.group_name = f"link_{link_id}"

        await self.channel_layer.group_add(self.group_name, self.channel_name)

        current_visit_count = await self._get_link_visit_count()

        await self.send_json({"type": "linkvisit_initial_count", "data": current_visit_count})

    async def new_visit(self, event):
        """Fires when a new link visit is created."""

        current_visit_count = await self._get_link_visit_count()
        await self.send_json({"type": "linkvisit_update_count", "data": current_visit_count})
