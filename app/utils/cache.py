import hashlib
from collections import OrderedDict

from django.core.cache import cache


def generate_cache_key(cache_prefix: str, **kwargs):
    """Create cache pair for poll previews, uses cache_prefix for unique entries and kwargs for unique properties"""
    unique_items_str = ""
    for _, value in kwargs.items():
        unique_items_str += str(value) + "-"

    preencoded_string = cache_prefix + "-" + unique_items_str[:-1]
    encoded_string = preencoded_string.encode()
    hash_hex = hashlib.md5(encoded_string).hexdigest()
    return hash_hex


def set_cache(value, cache_prefix: str, **kwargs):
    """Set preview cache for related cache pair, uses generate_poll_preview_cache"""
    cache_key = generate_cache_key(cache_prefix, **kwargs)
    cache.set(cache_key, value)


def check_cache(cache_prefix: str, **kwargs) -> list | OrderedDict:
    """Check if pair exists in cache, returns None if it doesn't"""
    cache_key = generate_cache_key(cache_prefix, **kwargs)
    return cache.get(cache_key)


def clear_cache(cache_prefix: str):
    """Clear a cache by the prefix before you repopulate"""
    cache.delete_many(keys=cache.keys(f"{cache_prefix}*"))
