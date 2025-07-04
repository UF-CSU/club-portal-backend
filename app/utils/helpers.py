import re
from urllib.parse import urljoin

from django.http import HttpRequest
from django.urls import reverse
from django.utils.module_loading import import_string

from app.settings import BASE_URL, CLIENT_URL


def reverse_query(viewname, query=None, **kwargs):
    """Wraps django's reverse function to add query params."""
    query = query if query else {}

    return (
        reverse(viewname, **kwargs)
        + ("?" if len(query.keys()) > 0 else "")
        + "&".join([f"{key}={value}" for key, value in query.items()])
    )


def get_client_ip(request: HttpRequest) -> str:
    """
    Get IP Address from request.

    First checks if the request has an HTTP_X_FORWARDED_FOR header,
    otherwise it will use the default ip header.
    """
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        ip = x_forwarded_for.split(",")[0]
    else:
        ip = request.META.get("REMOTE_ADDR")

    return ip


def get_full_url(path: str):
    """Get full url of a sub path using root domain."""

    return urljoin(BASE_URL, path)


def get_client_url(path: str):
    """Get the full url for the main client side."""

    return urljoin(CLIENT_URL, path)


def get_import_path(symbol):
    """
    Get a string version of class or function to be imported by
    a celery task or other thread operation.

    Parameters
    ----------
        - symbol (class, callable): The class, function, or other object to get import string of.

    Example
    -------
    ```
    # file_one.py
    class Something:
        pass

    obj_path = get_import_path(Something)

    # file_two.py
    Something = import_from_path(obj_path)
    ```
    """

    return f"{symbol.__module__}.{symbol.__qualname__}"


def import_from_path(path: str):
    """
    Get a symbol from its import path.

    Reverse function for `get_import_path`.
    Wraps django's default `import_string` function.
    """

    return import_string(path)


def clean_list(target: list):
    """Remove None values and empty strings from list."""

    return [item for item in target if item is not None and item != ""]


def str_to_list(target: str | None):
    """
    Split string into list using comma as a separator,
    skips commas surrounded by quotes.
    """
    if not isinstance(target, str):
        return []

    # items = target.split(r',(?=(?:[^"]*"[^"]*")*[^"]*$)')
    items = re.split(',(?=(?:[^"]*"[^"]*")*[^"]*$)', target)
    items = clean_list([str(item).strip().replace('"', "") for item in items])

    return items
