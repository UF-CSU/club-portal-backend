from asgiref.sync import sync_to_async
from core.abstracts.consumers import ConsumerBase

from .services import PollService


class PollSubmissionConsumer(ConsumerBase):
    async def connect(self):
        connected = await super().connect()
        if not connected:
            return

        self.poll_id = self.scope["url_route"]["kwargs"]["poll_id"]
        self.group_name = f"poll_{self.poll_id}"

        await self.channel_layer.group_add(self.group_name, self.channel_name)

        # Send poll submissions received so far
        current_submissions = await sync_to_async(PollService.get_submissions)(
            self.poll_id
        )
        await self.send_json(
            {"type": "initial_submissions", "data": current_submissions}
        )

    async def submission_create(self, event):
        await self.send_json(
            {
                "type": "submission_create",
                "data": event["data"],
            }
        )

    async def submission_update(self, event):
        await self.send_json(
            {
                "type": "submission_update",
                "data": event["data"],
            }
        )

    async def submission_delete(self, event):
        await self.send_json(
            {
                "type": "submission_delete",
                "data": event["data"],
            }
        )
