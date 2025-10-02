from typing import Optional

from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.core.cache import cache
from django.db import models


def get_permission(
    perm_label: str, obj=None, fail_silently=False
) -> Optional[Permission]:
    """
    Returns a permission object based on the app label and codename.

    Parameters
    ----------
        perm_label (str) : Permission label syntax, ex: app.view_model
    """
    cache_res = cache.get(perm_label)
    if cache_res is not None:
        return cache_res

    app_label, codename = perm_label.split(".")
    try:
        content_types = ContentType.objects.filter(app_label=app_label)
        permission = Permission.objects.get(
            content_type__in=content_types, codename=codename
        )
        cache.set(perm_label, permission)
        return permission
    except (ContentType.DoesNotExist, Permission.DoesNotExist) as e:
        if fail_silently:
            return None
        else:
            e.add_note(f"With perm label: {perm_label}")
            raise e


def parse_permissions(perms: list | None, fail_silently=False) -> list[Permission]:
    """
    Returns a list of permissions based in perms argument.

    *Accepted input types*

        - id (int) : Will try to get permission by id
        - label (str) : Will try to get permission by label
        - model (Permission) : Will just use permission as is

    """
    if perms is None:
        return []

    perm_objects = []

    for perm in perms:
        try:
            if isinstance(perm, int):
                obj = Permission.objects.get(id=perm)
            elif isinstance(perm, str):
                obj = get_permission(perm, fail_silently=False)
            elif isinstance(perm, Permission):
                obj = perm
            else:
                raise ValueError(f"Unsupported permission input type: {type(perm)}")

            perm_objects.append(obj)
        except Exception as e:
            if fail_silently:
                continue

            raise e

    return perm_objects


def get_perm_label(perm: Permission):
    """Get permission label in the form of `app_label.codename`."""

    codename, app_label, _ = perm.natural_key()

    return "%s.%s" % (app_label, codename)


def get_perm_labels_for_model(model: type[models.Model]):
    """Return a list of permission labels for model."""

    content_type = ContentType.objects.get_for_model(model)
    permissions = Permission.objects.filter(content_type=content_type)

    return [get_perm_label(perm) for perm in permissions]
