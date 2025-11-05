from core.abstracts.services import ServiceBase
from django.http import HttpRequest
from utils.helpers import get_client_ip

from analytics.models import Link, LinkVisit


class LinkSvc(ServiceBase[Link]):
    """Manage business logic for links."""

    model = Link

    @property
    def redirect_url(self):
        return self.obj.target_url

    def record_visit(self, request: HttpRequest):
        """Some user has visited the link."""
        ipaddress = get_client_ip(request)

        visit, _ = LinkVisit.objects.get_or_create(link=self.obj, ipaddress=ipaddress)
        visit.increment()

        return visit
