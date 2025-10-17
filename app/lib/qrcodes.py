"""
Manage library for creating QR Codes.

Reference: https://realpython.com/python-generate-qr-code/
"""

from io import BytesIO

import segno
from django.core.files import File

from utils.files import get_unique_filename


def create_qrcode_image(url: str, file_prefix="qrcode"):
    """Create QR Code image, return file path."""

    name = get_unique_filename(prefix=file_prefix, ext="svg")

    qrcode_buffer = BytesIO()
    qrcode = segno.make_qr(url)
    qrcode.save(qrcode_buffer, kind='svg')

    return File(qrcode_buffer, name=name)
