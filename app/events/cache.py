import hashlib

from django.core.cache import cache
from django.db.models import QuerySet

from events.models import Event, EventHost


def generate_event_hash(club_id: int = None, is_anonymous: bool = True) -> str:
    """Generates a hash from the full paths and is_anonymous field"""
    preencoded_string = "events-" + str(int(is_anonymous)) + "-" + str(club_id)
    encoded_string = preencoded_string.encode()
    hash_hex = hashlib.md5(encoded_string).hexdigest()
    return hash_hex


def set_event_cache(club_id: int, is_anonymous: bool, response_data):
    """Caches events after list request"""
    cache_key = generate_event_hash(club_id=club_id, is_anonymous=is_anonymous)
    cache.set(cache_key, response_data)


def check_event_cache(club_id: int, is_anonymous: bool) -> list:
    """Returns the list of requested events or None if they do not exist in the cache"""
    cache_key = generate_event_hash(club_id=club_id, is_anonymous=is_anonymous)
    return cache.get(cache_key)


def delete_repopulate_event_cache(hosts: QuerySet[EventHost]):
    """Delete all hosts keys from event cache"""
    for host in hosts:
        cache.delete(generate_event_hash(club_id=host.pk, is_anonymous=False))
        cache.delete(generate_event_hash(club_id=host.pk, is_anonymous=True))

        set_event_cache(
            club_id=host.pk, is_anonymous=True, response_data=Event.objects.filter(id=host.pk)
        )
        set_event_cache(
            club_id=host.pk,
            is_anonymous=False,
            response_data=Event.objects.filter(id=host.pk),
        )
