from core.abstracts.admin import ModelAdminBase
from django.contrib import admin
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _
from users.models import Ticket
from utils.admin import other_info_fields

from analytics.models import Link, LinkVisit, QRCode


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


class LinkAdmin(ModelAdminBase):
    """Display links in admin."""

    list_display = ("__str__", "url_link", "visit_count")
    inlines = (LinkVisitInlineAdmin,)
    readonly_fields = (
        "total_visit_count",
        "url_link",
    )

    def total_visit_count(self, obj):
        return mark_safe(f'<span id="link-visit-count">{obj.visit_count}</span>')

    def url_link(self, obj):
        return mark_safe(
            f'<a href="{obj.tracking_url}" target="_blank">{obj.tracking_url}</a>'
        )

    def render_change_form(
        self, request, context, add=None, change=None, form_url=None, obj=None
    ):
        ticket, _ = Ticket.objects.get_or_create(user=request.user)
        context["ticket"] = ticket
        return super().render_change_form(request, context, add, change, form_url, obj)


admin.site.register(QRCode, QRCodeAdmin)
admin.site.register(Link, LinkAdmin)
