"""
Manage library for creating QR Codes.

Reference: https://realpython.com/python-generate-qr-code/
"""

import uuid

import segno
from django.utils import timezone

from utils.files import get_media_path


def create_qrcode_image(url: str):
    """Create QR Code image, return file path."""

    img_path = get_media_path(
        "core/qrcodes/",
        f"{uuid.uuid4()}-{timezone.now().strftime('%d-%m-%Y_%H:%M:%S')}.svg",
    )

    qrcode = segno.make_qr(url)
    qrcode.save(img_path)

    return img_path
