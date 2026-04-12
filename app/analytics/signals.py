from typing import Optional

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.db.models.signals import post_save
from django.dispatch import receiver
from lib.celery import delay_task

from analytics.models import LinkVisit, QRCode
from analytics.tasks import generate_qrcode_image_task


@receiver(post_save, sender=QRCode)
def on_save_qrcode(sender, instance: Optional[QRCode], **kwargs):
    if instance.image:
        return

    delay_task(generate_qrcode_image_task, instance.pk)


@receiver(post_save, sender=LinkVisit)
def on_save_linkvisit(sender, instance: LinkVisit, created=False, **kwargs):
    """When a visit is recorded, send updates to websocket."""

    channel_layer = get_channel_layer()

    event = {
        "type": "new_visit",
    }

    async_to_sync(channel_layer.group_send)(f"link_{instance.link.pk}", event)
