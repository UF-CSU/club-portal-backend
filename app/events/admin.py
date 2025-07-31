from django.contrib import admin

from core.abstracts.admin import ModelAdminBase
from events.models import (
    Event,
    EventAttendance,
    EventAttendanceLink,
    EventHost,
    EventTag,
    RecurringEvent,
)
from events.serializers import EventAttendanceCsvSerializer, EventCsvSerializer
from events.services import EventService
from events.tasks import sync_recurring_event_task
from lib.celery import delay_task


class RecurringEventAdmin(admin.ModelAdmin):

    list_display = (
        "__str__",
        "days",
        "location",
        "start_date",
        "end_date",
    )
    actions = ("sync_events",)
    filter_horizontal = ("other_clubs",)

    @admin.action(description="Sync Events")
    def sync_events(self, request, queryset):

        for recurring in queryset.all():
            delay_task(sync_recurring_event_task, recurring_event_id=recurring.id)
            # RecurringEventService(recurring).sync_events()

        return


class EventAttendanceAdmin(ModelAdminBase):
    """Admin config for event attendance."""

    csv_serializer_class = EventAttendanceCsvSerializer

    list_display = ("event", "user")

    search_fields = (
        "event__name",
        "user__username",
    )

    list_filter = (
        "event__name",
        "user__username",
    )


class EventAttendanceInlineAdmin(admin.TabularInline):
    """List event attendees in event admin."""

    model = EventAttendance
    extra = 0
    readonly_fields = ("created_at",)

    def has_add_permission(self, request, *args, **kwargs):
        return False


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


class EventHostInlineAdmin(admin.TabularInline):
    """Manage clubs hosting events."""

    model = EventHost
    extra = 1


class EventAdmin(ModelAdminBase):
    """Admin config for club events."""

    csv_serializer_class = EventCsvSerializer

    list_display = (
        "__str__",
        "id",
        "location",
        "host_clubs",
        "start_at",
    )
    ordering = ("-start_at",)

    inlines = (
        EventHostInlineAdmin,
        EventAttendenceLinkInlineAdmin,
        EventAttendanceInlineAdmin,
    )
    actions = ("sync_attendance_links",)
    # TODO: Make sure only host attachments are available
    filter_horizontal = (
        "tags",
        "attachments",
    )
    search_fields = ("hosts__club__name", "hosts__club__alias")

    def host_clubs(self, obj):
        return ", ".join(list(obj.hosts.all().values_list("club__alias", flat=True)))

    @admin.action(description="Sync Attendence Links")
    def sync_attendance_links(self, request, queryset):
        """For all events, sync attendance links."""

        for event in queryset:
            EventService(event).sync_hosts_attendance_links()


admin.site.register(Event, EventAdmin)
admin.site.register(EventAttendance, EventAttendanceAdmin)
admin.site.register(EventTag)
admin.site.register(RecurringEvent, RecurringEventAdmin)
