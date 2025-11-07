import hashlib
from collections import OrderedDict

from django.core.cache import cache

from clubs.models import Club
from clubs.serializers import ClubPreviewSerializer


def generate_preview_hash(is_csu_partner: bool = False) -> str:
    """Generates a hash based on a if clubs are csu partners"""
    preencoded_string = "club-previews-" + str(is_csu_partner)
    encoded_string = preencoded_string.encode()
    hash_hex = hashlib.md5(encoded_string).hexdigest()
    return hash_hex


def set_preview_cache(is_csu_partner: bool, value):
    """Caches previews after list request"""
    cache_key = generate_preview_hash(is_csu_partner)
    cache.set(cache_key, value)


def check_preview_detail_cache(club_id: int) -> OrderedDict:
    """Returns the detail for a club preview or None if it does not exist"""
    pass


def check_preview_list_cache(is_csu_partner: bool) -> list:
    """Returns the list of requested previews or None if they do not exist in the cache"""
    cache_key = generate_preview_hash(is_csu_partner)
    return cache.get(cache_key)


def delete_repopulate_preview_cache():
    """Delete all hosts keys from previews cache"""
    cache.delete(generate_preview_hash(False))
    cache.delete(generate_preview_hash(True))

    set_preview_cache(
        True, ClubPreviewSerializer(Club.objects.filter(is_csu_partner=True), many=True).data
    )
    set_preview_cache(
        False, ClubPreviewSerializer(Club.objects.filter(is_csu_partner=False), many=True).data
    )
