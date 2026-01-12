from datetime import date, datetime, timedelta
from typing import Optional

from clubs.models import Club, ClubFile
from core.abstracts.viewsets import (
    FilterBackendBase,
    ModelPreviewViewSetBase,
    ModelViewSetBase,
    ObjectViewPermissions,
    ViewSetBase,
)
from dateutil.relativedelta import relativedelta
from django.db.models import Prefetch, Q, QuerySet
from django.utils import timezone
from lib.celery import delay_task
from rest_framework import permissions, status
from rest_framework.pagination import BasePagination
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView
from utils.dates import parse_date
from utils.views import Query, query_params

from events.models import (
    Event,
    EventAttendanceLink,
    EventCancellation,
    EventHost,
    EventTag,
)
from events.services import EventService
from events.tasks import sync_recurring_event_task

from . import models, serializers


class CustomDatePagination(BasePagination):
    """Allow api pagination via start and end date."""

    default_shift = timedelta(days=7)

    def get_date_range(self, request: Request):
        """Get start and end dates from url."""
        start_date = request.query_params.get("start_date", None)
        end_date = request.query_params.get("end_date", None)

        current_tz = timezone.get_current_timezone()
        now = datetime.now().astimezone(current_tz)

        # Parse start date
        if start_date is None:
            start_date = now.date()
        else:
            start_date = parse_date(start_date)

        if start_date:
            start_date = timezone.datetime(
                start_date.year, start_date.month, start_date.day, tzinfo=current_tz
            )

        # Parse end date
        if end_date is None:
            end_date = (now + self.default_shift).date()
        else:
            end_date = parse_date(end_date)

        if end_date:
            end_date = timezone.datetime(
                end_date.year,
                end_date.month,
                end_date.day,
                hour=23,
                minute=59,
                second=59,
                tzinfo=current_tz,
            )

        return (start_date, end_date)

    def paginate_queryset(self, queryset: QuerySet[Event], request, view=None):
        self.start_date, self.end_date = self.get_date_range(request)

        query = Q()
        start_query = Q(end_at__gte=self.start_date)
        end_query = Q(start_at__lte=self.end_date)

        if self.start_date and self.end_date:
            query = start_query & end_query
        elif self.start_date:
            query = start_query
        elif self.end_date:
            query = end_query

        queryset = queryset.filter(query)
        self.count = queryset.count()

        return queryset

    def get_paginated_response(self, data):
        return Response(
            {
                "count": self.count,
                "start_date": self.start_date.date()
                if self.start_date is not None
                else None,
                "end_date": self.end_date.date() if self.end_date is not None else None,
                "results": data,
            }
        )

    def get_paginated_response_schema(self, schema):
        return {
            "type": "object",
            "required": ["count", "start_date", "end_date", "results"],
            "properties": {
                "count": {
                    "type": "integer",
                    "example": 123,
                },
                "start_date": {
                    "type": "date",
                    "nullable": False,
                    "example": datetime.now().replace(day=1).strftime("%Y-%m-%d"),
                },
                "end_date": {
                    "type": "date",
                    "nullable": False,
                    "example": datetime.now().replace(day=25).strftime("%Y-%m-%d"),
                },
                "results": schema,
            },
        }

    def get_schema_operation_parameters(self, view):
        parameters = [
            {
                "name": "start_date",
                "required": False,
                "in": "query",
                "description": "Will return events starting after midnight of this date.",
                "schema": {"type": "date"},
            },
            {
                "name": "end_date",
                "required": False,
                "in": "query",
                "description": "Will return events starting at a time before midnight of this date.",
                "schema": {"type": "date"},
            },
        ]
        return parameters


class EventPreviewViewSet(ModelPreviewViewSetBase):
    """API For showing public event previews."""

    queryset = Event.objects.filter(Q(is_public=True) & Q(is_draft=False))
    serializer_class = serializers.EventPreviewSerializer
    pagination_class = CustomDatePagination


class EventClubFilter(FilterBackendBase):
    """Get events filtered by club"""

    pass


class EventViewset(ModelViewSetBase):
    """CRUD Api routes for Event models."""

    queryset = (
        Event.objects.all()
        .select_related("recurring_event", "_poll")
        .prefetch_related(
            Prefetch(
                "hosts",
                queryset=EventHost.objects.select_related("club", "club__logo").only(
                    "id",
                    "event_id",
                    "club_id",
                    "is_primary",
                    "club__id",
                    "club__name",
                    "club__alias",
                    "club__logo_id",
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
                queryset=ClubFile.objects.only(
                    "file",
                ),
            ),
            Prefetch(
                "attendance_links",
                queryset=EventAttendanceLink.objects.select_related("link_ptr"),
            ),
        )
    )
    serializer_class = serializers.EventSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ["clubs"]
    pagination_class = CustomDatePagination

    def get_serializer_class(self):
        with_analytics = self.request.query_params.get(
            "analytics", "False"
        ).capitalize()
        if with_analytics == "True":
            return serializers.EventAnalyticsSerializer
        return super().get_serializer_class()

    def get_queryset(self):
        return self.queryset.filter_for_user(self.request.user)

    def filter_queryset(self, queryset):
        if self.action == "retrieve":
            return queryset

        return super().filter_queryset(queryset)

    def check_permissions(self, request):
        obj_permission = ObjectViewPermissions()
        if not obj_permission.has_permission(request, self):
            self.permission_denied(
                request,
                message=getattr(obj_permission, "message", None),
                code=getattr(obj_permission, "code", None),
            )

        return super().check_permissions(request)

    def check_object_permissions(self, request, obj):
        obj_permission = ObjectViewPermissions()
        if not obj_permission.has_object_permission(request, self, obj):
            self.permission_denied(
                request,
                message=getattr(obj_permission, "message", None),
                code=getattr(obj_permission, "code", None),
            )

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

        if not self.request.user.has_perm("events.add_event", is_global=True):
            if not user_clubs.filter(id__in=club_ids).exists():
                self.permission_denied(
                    self.request,
                    "Can only create events which include the user's club as a host",
                )
            elif not primary_club or not user_clubs.filter(id=primary_club.id).exists():
                self.permission_denied(
                    self.request,
                    "Need event creation privilege for primary host club.",
                )

        return super().perform_create(serializer)

    @query_params(
        analytics=Query(
            required=False,
            qtype=bool,
            default=False,
            description="A field for returning analytics",
        )
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @query_params(
        analytics=Query(
            required=False,
            qtype=bool,
            default=False,
            description="A field for returning analytics",
        )
    )
    def list(self, request: Request, *args, **kwargs):
        return super().list(request, *args, **kwargs)


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

        super().perform_create(serializer)

        # Schedule the recurring event for syncing
        delay_task(sync_recurring_event_task, recurring_event_id=serializer.instance.id)

    def perform_update(self, serializer):
        super().perform_update(serializer)

        # Schedule the recurring event for syncing
        delay_task(sync_recurring_event_task, recurring_event_id=serializer.instance.id)


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


class EventHeatmapViewSet(APIView):
    """Get count of events for each day in range."""

    permission_classes = [permissions.IsAuthenticated]  # TODO: RBAC for event heatmap
    authentication_classes = ViewSetBase.authentication_classes
    serializer_class = serializers.EventHeatmapSerializer

    @query_params(
        clubs=Query(qtype=int, is_list=True),
        start_date=Query(qtype=date),
        end_date=Query(qtype=date),
    )
    def get(
        self,
        request: Request,
        clubs: Optional[list[int]] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ):
        # Parse club ids
        if clubs is None:
            clubs = list(
                Club.objects.filter_for_user(request.user).values_list("id", flat=True)
            )

        # Get start/end dates
        now = datetime.now()
        if start_date is None:
            start_date = (
                datetime(year=now.year, month=now.month, day=1)
                # Go 2 months back from beginning of month
                - relativedelta(months=2)
            ).date()

        if end_date is None:
            end_date = (
                datetime(year=now.year, month=now.month, day=1)
                # Go to end of this month
                + relativedelta(months=1)
                - timedelta(days=1)
                # Go 2 months ahead of this month's end
                + relativedelta(months=2)
            ).date()

        # Generate heatmap
        heatmap = EventService.get_event_heatmap(
            club_ids=clubs, start_date=start_date, end_date=end_date
        )

        serializer = self.serializer_class(heatmap)

        return Response(data=serializer.data)
