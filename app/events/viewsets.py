from rest_framework import status
from rest_framework.response import Response

from clubs.models import Club
from core.abstracts.viewsets import ModelViewSetBase
from events.models import Event, EventAttendance, EventCancellation

from . import models, serializers


class EventViewset(ModelViewSetBase):
    """CRUD Api routes for Event models."""

    queryset = models.Event.objects.all().prefetch_related(
        "hosts", "hosts__club", "tags"
    )
    serializer_class = serializers.EventSerializer

    def filter_queryset(self, queryset):
        clubs = self.request.query_params.getlist("clubs", None)

        if clubs:
            queryset = queryset.filter(hosts__club__id__in=clubs)

        return super().filter_queryset(queryset)

    def check_object_permissions(self, request, obj):
        if self.action == "retrieve":
            return True
        return super().check_object_permissions(request, obj)

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

        if not self.request.user.has_perm("events.add_recurringevent", is_global=True):
            if not user_clubs.filter(id__in=club_ids).exists():
                self.permission_denied(
                    self.request,
                    "Can only create recurring events which include the user's club as a host",
                )
            elif not primary_club or not user_clubs.filter(id=primary_club.id).exists():
                self.permission_denied(
                    self.request,
                    "Need recurring event creation priviledge for primary host club.",
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


class EventAttendanceViewSet(ModelViewSetBase):
    queryset = EventAttendance.objects.all()
    serializer_class = serializers.EventAttendanceSerializer


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
