from asgiref.sync import async_to_sync
from celery import shared_task
from channels.layers import get_channel_layer

from lib.qrcodes import create_qrcode_image


@shared_task
def generate_qrcode_image_task(qrcode_pk: int):
    """Generate and save QR code image in a background Celery worker."""

    from analytics.models import QRCode

    try:
        instance = QRCode.objects.get(pk=qrcode_pk)
    except QRCode.DoesNotExist:
        return

    if instance.image:
        return

    img = create_qrcode_image(instance.url)
    instance.image = img
    instance.save()

    # Notify poll editor if this QR code belongs to a poll submission link
    try:
        poll_submission_link = instance.link.pollsubmissionlink
    except Exception:
        return

    from polls.models import Poll
    from polls.serializers import PollSerializer

    poll = (
        Poll.objects.filter(pk=poll_submission_link.poll_id)
        .select_related("club", "event")
        .prefetch_related("_submission_link__qrcode")
        .first()
    )
    if poll is None:
        return

    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        f"poll_{poll.pk}",
        {"type": "poll_update", "data": PollSerializer(poll).data},
    )
