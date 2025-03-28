"""
Route requests to analytics app.
"""

from django.http import HttpRequest
from django.shortcuts import redirect

from analytics.services import LinkSvc


def redirect_link_view(request: HttpRequest, link_id: int):
    """Ping link, redirect to target url."""

    service = LinkSvc(link_id)
    service.record_visit(request)

    return redirect(service.redirect_url)
