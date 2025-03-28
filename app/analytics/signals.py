from typing import Optional

from django.db.models.signals import post_save
from django.dispatch import receiver

from analytics.models import QRCode
from lib.qrcodes import create_qrcode_image


@receiver(post_save, sender=QRCode)
def on_save_qrcode(sender, instance: Optional[QRCode], **kwargs):
    if instance.image:
        return

    img_path = create_qrcode_image(instance.url)
    instance.save_image(img_path)
