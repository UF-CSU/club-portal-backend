from django.contrib import admin

from events.models import (
    Event,
    EventAttendance,
    EventAttendanceLink,
    EventTag,
    RecurringEvent,
)
from events.services import EventService


# Register your models here.
class RecurringEventAdmin(admin.ModelAdmin):

    list_display = (
        "__str__",
        "day",
        "location",
        "start_date",
        "end_date",
    )
    actions = ("sync_events",)

    @admin.action(description="Sync Events")
    def sync_events(self, request, queryset):

        for recurring in queryset.all():
            EventService.sync_recurring_event(recurring)

        return


class EventAttendanceInlineAdmin(admin.TabularInline):
    """List event attendees in event admin."""

    model = EventAttendance
    extra = 0
    readonly_fields = ("created_at",)


class EventAttendenceLinkInlineAdmin(admin.StackedInline):
    """List event links in event admin."""

    model = EventAttendanceLink
    readonly_fields = (
        "target_url",
        "club",
        "tracking_url_link",
    )
    extra = 0

    def tracking_url_link(self, obj):
        return obj.as_html()


class EventAdmin(admin.ModelAdmin):
    """Admin config for club events."""

    list_display = (
        "__str__",
        "id",
        "location",
        "start_at",
        "end_at",
    )
    ordering = ("start_at",)

    inlines = (EventAttendenceLinkInlineAdmin, EventAttendanceInlineAdmin)
    filter_horizontal = ("tags",)


admin.site.register(Event, EventAdmin)
admin.site.register(EventTag)
admin.site.register(RecurringEvent, RecurringEventAdmin)
