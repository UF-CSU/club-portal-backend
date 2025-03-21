from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType


def get_permission(perm_label: str, obj=None):
    """
    Returns a permission object based on the app label and codename.

    Parameters
    ----------
        perm_label (str) : Permission label syntax, ex: app.view_model
    """

    app_label, codename = perm_label.split(".")
    try:
        if obj is None:
            content_types = ContentType.objects.filter(app_label=app_label)
        else:
            content_types = [ContentType.objects.get_for_model(obj)]

        permission = Permission.objects.get(
            content_type__in=content_types, codename=codename
        )
        return permission
    except (ContentType.DoesNotExist, Permission.DoesNotExist):
        return None
