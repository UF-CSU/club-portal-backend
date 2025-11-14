import hashlib
from collections import OrderedDict

from clubs.models import Club
from django.core.cache import cache
from events.models import Event

from polls.models import Poll, PollField, PollSubmissionLink
from polls.serializers import PollPreviewSerializer

LIST_POLL_PREVIEW_PREFIX = "poll-previews"
DETAIL_POLL_PREVIEW_PREFIX = "poll-preview"


def generate_poll_preview_cache_key(cache_prefix: str, **kwargs):
    """Create cache pair for poll previews, uses cache_prefix for unique entries and kwargs for unique properties"""
    unique_items_str = ""
    for _, value in kwargs.items():
        unique_items_str += str(value) + "-"

    preencoded_string = cache_prefix + "-" + unique_items_str[:-1]
    encoded_string = preencoded_string.encode()
    hash_hex = hashlib.md5(encoded_string).hexdigest()
    return hash_hex


def set_poll_preview_cache(value, cache_prefix: str, **kwargs):
    """Set preview cache for related cache pair, uses generate_poll_preview_cache"""
    cache_key = generate_poll_preview_cache_key(cache_prefix, **kwargs)
    cache.set(cache_key, value)


def check_poll_preview_cache(cache_prefix: str, **kwargs) -> list | OrderedDict:
    """Check if pair exists in cache, returns None if it doesn't"""
    cache_key = generate_poll_preview_cache_key(cache_prefix, **kwargs)
    return cache.get(cache_key)


def delete_repopulate_poll_preview_cache(
    instance: Poll | Event | Club | PollField | PollSubmissionLink,
):
    """Invalidates and fixes cache, loops through passed objects for repopulation"""
    id: int = instance.pk
    if isinstance(instance, Poll):
        set_poll_preview_cache(
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

    set_poll_preview_cache(
        PollPreviewSerializer(Poll.objects.all(), many=True).data,
        LIST_POLL_PREVIEW_PREFIX,
    )


def poll_preview_repopulate_helper(polls: list[Poll] | None):
    """Helper to repopulate poll preview cache"""
    if not polls:
        return

    for poll in polls:
        set_poll_preview_cache(
            PollPreviewSerializer(Poll.objects.find_by_id(poll.pk)).data,
            DETAIL_POLL_PREVIEW_PREFIX,
            poll_id=poll.pk,
        )
