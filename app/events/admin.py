from django import forms
from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from core.abstracts.admin import ModelAdminBase, StackedInlineBase, TabularInlineBase
from events.models import (
    Event,
    EventAttendance,
    EventAttendanceLink,
    EventHost,
    EventTag,
    RecurringEvent,
)
from events.serializers import EventAttendanceCsvSerializer, EventCsvSerializer
from events.tasks import sync_event_attendance_links_task, sync_recurring_event_task
from lib.celery import delay_task
from polls.models import Poll
from utils.admin import other_info_fields
from utils.formatting import plural_noun_display


class RecurringEventAdmin(admin.ModelAdmin):
    list_display = (
        "__str__",
        "days",
        "event_count",
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

    def event_count(self, obj):
        return obj.events.all().count()


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

    readonly_fields = ("id", "poll_submission_link", *ModelAdminBase.readonly_fields)
    fieldsets = (
        (
            None,
            {"fields": ("id", "event", "user", "poll_submission_link")},
        ),
        other_info_fields,
    )

    def poll_submission_link(self, obj):
        return self.as_model_link(obj.poll_submission)


class EventAttendanceInlineAdmin(TabularInlineBase):
    """List event attendees in event admin."""

    model = EventAttendance
    extra = 0
    readonly_fields = (
        "link",
        "created_at",
    )

    def has_add_permission(self, request, *args, **kwargs):
        return False

    def link(self, obj):
        return self.as_model_link(obj, text="View")


class EventAttendenceLinkInlineAdmin(StackedInlineBase):
    """List event links in event admin."""

    model = EventAttendanceLink
    readonly_fields = (
        "club",
        "target_url",
        "url_link",
    )
    extra = 0

    def url_link(self, obj):
        return self.as_link(obj.url)


class EventHostInlineAdmin(admin.TabularInline):
    """Manage clubs hosting events."""

    model = EventHost
    extra = 1


class EventForm(forms.ModelForm):
    """Determine the fields for events in admin."""

    poll = forms.ModelChoiceField(queryset=Poll.objects.all(), required=False)

    class Meta:
        model = Event
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if self.instance:
            self.fields["poll"].initial = Poll.objects.find_one(
                event__id=self.instance.id
            )

    def save(self, commit=False):
        poll = self.cleaned_data.pop("poll", None)
        event = super().save(commit)

        if poll:
            poll.event = event
            if commit:
                poll.save()
        else:
            Poll.objects.filter(event__id=event.id).update(event=None)

        return event


class EventAdmin(ModelAdminBase):
    """Admin config for club events."""

    csv_serializer_class = EventCsvSerializer
    form = EventForm

    list_display = (
        "__str__",
        "id",
        "location",
        "host_clubs",
        "start_at",
        "status",
        "duration",
    )
    ordering = ("-start_at",)

    inlines = (
        EventHostInlineAdmin,
        EventAttendanceInlineAdmin,
        EventAttendenceLinkInlineAdmin,
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

        event_ids = list(queryset.values_list("id", flat=True))
        delay_task(sync_event_attendance_links_task, event_ids=event_ids)

        self.message_user(
            request,
            message=f"Successfully scheduled to sync attendance links for {plural_noun_display(queryset, 'event')}.",
        )

        return

    fieldsets = (
        (
            None,
            {
                "fields": (
                    "id",
                    "name",
                    "event_type",
                    "description",
                    "location",
                    "start_at",
                    "end_at",
                    "is_draft",
                    # "is_poll_submission_required",
                    "enable_attendance",
                )
            },
        ),
        (_("Public Scheduling"), {"fields": ("is_public", "make_public_at")}),
        (
            _("Relationships"),
            {
                "fields": (
                    "recurring_event",
                    "poll",
                    "tags",
                    "attachments",
                )
            },
        ),
    )


admin.site.register(Event, EventAdmin)
admin.site.register(EventAttendance, EventAttendanceAdmin)
admin.site.register(EventTag)
admin.site.register(RecurringEvent, RecurringEventAdmin)
