"""
Route requests to analytics app.
"""

from django.http import FileResponse, HttpRequest
from django.shortcuts import get_object_or_404, redirect

from analytics.models import QRCode
from analytics.services import LinkSvc


def redirect_link_view(request: HttpRequest, link_id: int):
    """Ping link, redirect to target url."""

    service = LinkSvc(link_id)
    service.record_visit(request)

    return redirect(service.redirect_url)


def download_qrcode_view(request: HttpRequest, id: int):
    """Download qrcode as attachment."""

    qrcode = get_object_or_404(QRCode, pk=id)
    return FileResponse(qrcode.image.open("rb"), as_attachment=True)
