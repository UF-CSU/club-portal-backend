from django.contrib import admin
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _

from analytics.models import Link, LinkVisit, QRCode
from core.abstracts.admin import ModelAdminBase
from utils.admin import other_info_fields


class QRCodeAdmin(ModelAdminBase):
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
        return self.as_image(obj.image)


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
