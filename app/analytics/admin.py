from django.contrib import admin
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _

from analytics.models import Link, LinkVisit, QRCode
from utils.admin import other_info_fields


class QRCodeAdmin(admin.ModelAdmin):
    """Admin config for QR Codes."""

    readonly_fields = (
        "created_at",
        "updated_at",
        "size",
        "preview",
    )

    fieldsets = (
        (
            None,
            {
                "fields": ("preview", "image"),
            },
        ),
        (
            _("Details"),
            {"fields": ("size", "link")},
        ),
        other_info_fields,
    )

    def preview(self, obj):
        if not obj.image:
            return None

        return mark_safe(
            "<svg width='90' height='90' style='background-color:white'>"
            f"<image  xlink:href={obj.image.url} width='100%'>"
            "</svg>"
        )


class LinkVisitInlineAdmin(admin.StackedInline):
    """Display link visits in link admin."""

    model = LinkVisit
    extra = 0

    def has_add_permission(self, request, *args, **kwargs):
        return False

    def has_change_permission(self, request, *args, **kwargs):
        return False


class LinkAdmin(admin.ModelAdmin):
    """Display links in admin."""

    list_display = ("__str__", "url_link", "link_visits")
    inlines = (LinkVisitInlineAdmin,)

    def url_link(self, obj):
        return mark_safe(
            f'<a href="{obj.tracking_url}" target="_blank">{obj.tracking_url}</a>'
        )


admin.site.register(QRCode, QRCodeAdmin)
admin.site.register(Link, LinkAdmin)
