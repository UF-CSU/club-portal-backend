from django.http import HttpRequest

from analytics.models import Link, LinkVisit
from core.abstracts.services import ServiceBase
from utils.helpers import get_client_ip


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
