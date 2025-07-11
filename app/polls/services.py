from core.abstracts.services import ServiceBase
from polls.models import Poll, PollTemplate


class PollTemplateService(ServiceBase[PollTemplate]):
    """Business logic for polls."""

    model = PollTemplate

    def create_poll(self) -> Poll:
        """Create a new poll from this one if it is a template."""

        pass
