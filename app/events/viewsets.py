from django.db.models import Q
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework import mixins, permissions, status
from rest_framework.response import Response

from clubs.models import Club
from core.abstracts.viewsets import (
    CustomLimitOffsetPagination,
    ModelViewSetBase,
    ObjectViewPermissions,
    ViewSetBase,
)
from events.models import Event, EventAttendance, EventCancellation

from . import models, serializers


class EventViewset(ModelViewSetBase):
    """CRUD Api routes for Event models."""

    queryset = models.Event.objects.all().prefetch_related(
        "hosts", "hosts__club", "tags"
    )
    serializer_class = serializers.EventSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    filterset_fields = ["clubs"]

    def get_queryset(self):
        qs = super().get_queryset()

        if self.request.user.is_anonymous:
            return qs.filter(Q(is_public=True) & Q(is_draft=False))

        return qs

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


class EventAttendanceViewSet(
    mixins.CreateModelMixin, mixins.ListModelMixin, ViewSetBase
):
    queryset = EventAttendance.objects.all()
    serializer_class = serializers.EventAttendanceSerializer
    # permission_classes = [permissions.IsAuthenticated, ObjectViewPermissions]
    pagination_class = CustomLimitOffsetPagination

    def check_permissions(self, request):
        # This runs before `get_queryset`, will short-circuit out if event
        # does not exist

        event_id = int(self.kwargs.get("event_id"))
        self.event = get_object_or_404(Event, id=event_id)

        if self.action == "create":
            return True

        super().check_permissions(request)

    def perform_create(self, serializer):
        data = {"event": self.event}

        # Pass request user if authenticated
        if self.request.user.is_authenticated:
            data["request_user"] = self.request.user

        serializer.save(**data)

    @extend_schema(auth=[{"security": []}, {}])
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)


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
