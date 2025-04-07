from django.contrib import admin
from django.utils.translation import gettext_lazy as _

other_info_fields = (
    (
        (
            _("Other Information"),
            {
                "fields": (
                    "created_at",
                    "updated_at",
                ),
                "classes": ("collapse",),
            },
        ),
    )
    .__iter__()
    .__next__()
)

__all__ = ("other_info_fields",)


def get_admin_context(request, extra_context=None):
    """Get default context dict for the admin site."""

    return {**admin.site.each_context(request), **(extra_context or {})}


def get_model_admin_reverse(admin_name, model, url_context):
    """Format info to proper reversable format."""

    info = (
        admin_name,
        model._meta.app_label,
        model._meta.model_name,
        url_context,
    )

    return "%s:%s_%s_%s" % info
