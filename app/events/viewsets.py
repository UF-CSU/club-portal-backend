from datetime import timedelta

from clubs.models import Club, ClubFile
from core.abstracts.viewsets import (
    FilterBackendBase,
    ModelViewSetBase,
    ObjectViewPermissions,
)
from django.db.models import Prefetch, Q
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import permissions, status
from rest_framework.response import Response

from events.models import (
    Event,
    EventAttendanceLink,
    EventCancellation,
    EventHost,
    EventTag,
)

from . import models, serializers


class EventClubFilter(FilterBackendBase):
    """Get events filtered by club"""


class EventDateFilter(FilterBackendBase):
    """Get events ordered by date"""

    filter_fields = [
        {"name": "start_at", "schema_type": "datetime"},
        {"name": "end_at", "schema_type": "datetime"},
    ]

    allowed_fields = {"start_at", "end_at"}

    class Meta:
        model = Event
        fields = ["date_fields"]

    def filter_queryset(self, request, queryset, view):
        start_date = request.query_params.get("start_at")
        end_date = request.query_params.get("end_at")

        # Assuming we should only check if it is within day boundary
        today = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
        shift = timedelta(days=14)

        if start_date is None and end_date is None:
            return queryset.filter(
                Q(start_at__lte=today + shift) & Q(end_at__gte=today - shift)
            )

        if start_date is not None:
            queryset = queryset.filter(end_at__gte=start_date)
        else:
            queryset = queryset.filter(end_at__gte=today - shift)

        if end_date is not None:
            queryset = queryset.filter(start_at__lte=end_date)
        else:
            queryset = queryset.filter(start_at__lte=today + shift)

        return queryset


class EventViewset(ModelViewSetBase):
    """CRUD Api routes for Event models."""

    queryset = (
        Event.objects.all()
        .select_related("recurring_event", "_poll")
        .prefetch_related(
            Prefetch(
                "hosts",
                queryset=EventHost.objects.select_related(
                    "club", "club__logo", "club__banner"
                ).only(
                    "id",
                    "event_id",
                    "club_id",
                    "is_primary",
                    "club__id",
                    "club__name",
                    "club__alias",
                    "club__logo_id",
                    "club__banner_id",
                    "club__primary_color",
                    "club__text_color",
                ),
            ),
            Prefetch(
                "tags",
                queryset=EventTag.objects.order_by("order", "name").only(
                    "id", "name", "color", "order"
                ),
            ),
            Prefetch(
                "attachments",
                queryset=ClubFile.objects.only("id", "file", "display_name", "club_id"),
            ),
            Prefetch(
                "attendance_links",
                queryset=EventAttendanceLink.objects.select_related("link_ptr"),
            ),
        )
    )
    serializer_class = serializers.EventSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    filter_backends = [EventDateFilter, DjangoFilterBackend]
    filterset_fields = ["clubs"]

    def get_queryset(self):
        qs = super().get_queryset()

        if self.request.user.is_anonymous:
            return qs.filter(Q(is_public=True) & Q(is_draft=False))

        return qs

    def filter_queryset(self, queryset):
        if self.action == "retrieve":
            return queryset

        return super().filter_queryset(queryset)

    def check_permissions(self, request):
        if self.action == "list" or self.action == "retrieve":
            return super().check_permissions(request)

        obj_permission = ObjectViewPermissions()
        if not obj_permission.has_permission(request, self):
            self.permission_denied(
                request,
                message=getattr(obj_permission, "message", None),
                code=getattr(obj_permission, "code", None),
            )

    def check_object_permissions(self, request, obj):
        # For GET method, just check if is authenticated
        if self.action == "retrieve":
            return super().check_object_permissions(request, obj)

        # Otherwise, check for individual permissions
        obj_permission = ObjectViewPermissions()
        if not obj_permission.has_object_permission(request, self, obj):
            self.permission_denied(
                request,
                message=getattr(obj_permission, "message", None),
                code=getattr(obj_permission, "code", None),
            )

    def perform_create(self, serializer):
        hosts = serializer.validated_data.get("hosts", [])

        if len(hosts) == 0 and not self.request.user.has_perm(
            "events.add_event", is_global=True
        ):
            self.permission_denied(self.request, message="Cannot create global events")

        club_ids = [host.get("club").id for host in hosts]
        user_clubs = Club.objects.filter_for_user(self.request.user)

        primary_club = None
        for host in hosts:
            if host.get("is_primary", False):
                primary_club = host.get("club")

        if not self.request.user.has_perm("events.add_event", is_global=True):
            if not user_clubs.filter(id__in=club_ids).exists():
                self.permission_denied(
                    self.request,
                    "Can only create events which include the user's club as a host",
                )
            elif not primary_club or not user_clubs.filter(id=primary_club.id).exists():
                self.permission_denied(
                    self.request,
                    "Need event creation priviledge for primary host club.",
                )

        return super().perform_create(serializer)


class RecurringEventViewSet(ModelViewSetBase):
    """CRUD Api routes for Recurring Events."""

    queryset = models.RecurringEvent.objects.all()
    serializer_class = serializers.RecurringEventSerializer

    def perform_create(self, serializer):
        club = serializer.validated_data.get("club", None)
        other_clubs = serializer.validated_data.get("other_clubs", None)
        club_ids = []

        if club:
            club_ids.append(club.id)
        if other_clubs:
            club_ids += [h.id for h in other_clubs]

        user_clubs = Club.objects.filter_for_user(self.request.user)

        # If the user's club is not a host, permission denied
        if not self.request.user.has_perm("events.add_recurringevent", is_global=True):
            if not user_clubs.filter(id__in=club_ids).exists():
                self.permission_denied(
                    self.request,
                    "Can only create recurring events which include the user's club as a host",
                )
            elif not user_clubs.filter(id=club.id).exists():
                self.permission_denied(
                    self.request,
                    "Need recurring event creation priviledge for primary host club.",
                )

        return super().perform_create(serializer)


class EventCancellationViewSet(ModelViewSetBase):
    queryset = EventCancellation.objects.all()
    serializer_class = serializers.EventCancellationSerializer

    def create(self, request, *args, **kwargs):
        event_id = request.data.get("event_id")
        reason = request.data.get("reason")
        cancelled_by = request.user
        event = Event.objects.get(pk=event_id)

        if event:
            cancellation = EventCancellation.objects.create(
                event=event, reason=reason, cancelled_by=cancelled_by
            )
            return Response(serializers.EventCancellationSerializer(cancellation).data)
        else:
            return Response(
                {"error": "Event not found"}, status=status.HTTP_404_NOT_FOUND
            )
