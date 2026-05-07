from lib.celery import debounced_task


@debounced_task(delay_sec=1)
def regenerate_poll_preview_cache_task(poll_ids: list[int] | None = None):
    """Delete and recreate poll preview cache in a background Celery worker."""

    from utils.cache import set_cache

    from polls.cache import (
        LIST_POLL_PREVIEW_PREFIX,
        poll_preview_repopulate_helper,
    )
    from polls.models import Poll
    from polls.serializers import PollPreviewSerializer

    if poll_ids:
        polls = Poll.objects.filter(id__in=poll_ids)
        poll_preview_repopulate_helper(polls)

    set_cache(
        PollPreviewSerializer(Poll.objects.all(), many=True).data,
        LIST_POLL_PREVIEW_PREFIX,
    )
