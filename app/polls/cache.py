from clubs.models import Club
from events.models import Event
from utils.cache import set_cache

from polls.models import Poll, PollField, PollSubmissionLink
from polls.serializers import PollPreviewSerializer

LIST_POLL_PREVIEW_PREFIX = "poll-previews"
DETAIL_POLL_PREVIEW_PREFIX = "poll-preview"


def delete_repopulate_poll_preview_cache(
    instance: Poll | Event | Club | PollField | PollSubmissionLink,
):
    """Invalidates and fixes cache, loops through passed objects for repopulation"""
    id: int = instance.pk
    if isinstance(instance, Poll):
        set_cache(
            PollPreviewSerializer(Poll.objects.find_by_id(id)).data,
            DETAIL_POLL_PREVIEW_PREFIX,
            poll_id=id,
        )
    if isinstance(instance, Event):
        polls = Poll.objects.find(event__id=id)
        poll_preview_repopulate_helper(polls)
    if isinstance(instance, Club):
        polls = Poll.objects.find(club__id=id)
        poll_preview_repopulate_helper(polls)
    if isinstance(instance, PollField):
        polls = Poll.objects.find(fields__id=id)
        poll_preview_repopulate_helper(polls)
    if isinstance(instance, PollSubmissionLink):
        polls = Poll.objects.find(_submission_link__id=id)
        poll_preview_repopulate_helper(polls)

    set_cache(
        PollPreviewSerializer(Poll.objects.all(), many=True).data,
        LIST_POLL_PREVIEW_PREFIX,
    )


def poll_preview_repopulate_helper(polls: list[Poll] | None):
    """Helper to repopulate poll preview cache"""
    if not polls:
        return

    for poll in polls:
        set_cache(
            PollPreviewSerializer(Poll.objects.find_by_id(poll.pk)).data,
            DETAIL_POLL_PREVIEW_PREFIX,
            poll_id=poll.pk,
        )
