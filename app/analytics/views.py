"""
Route requests to analytics app.
"""

from django.http import FileResponse, HttpRequest
from django.shortcuts import get_object_or_404, redirect

from analytics.models import QRCode
from analytics.services import LinkSvc
from utils.files import get_file_path


def redirect_link_view(request: HttpRequest, link_id: int):
    """Ping link, redirect to target url."""

    service = LinkSvc(link_id)
    service.record_visit(request)

    return redirect(service.redirect_url)


def download_qrcode_view(request: HttpRequest, id: int):
    """Download qrcode as attachment."""

    qrcode = get_object_or_404(QRCode, pk=id)

    return FileResponse(open(get_file_path(qrcode.image), "rb"), as_attachment=True)
