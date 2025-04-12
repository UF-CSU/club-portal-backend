from rest_framework import status, viewsets
from rest_framework.response import Response

from core.abstracts.viewsets import ModelViewSetBase
from events.models import Event, EventCancellation

from . import models, serializers


class EventViewset(ModelViewSetBase):
    """CRUD Api routes for Event models."""

    queryset = models.Event.objects.all()
    serializer_class = serializers.EventSerializer

    def get_queryset(self):
        # Filter by primary club
        primary_club = self.kwargs.get("primary_club", None)
        self.queryset = models.Event.objects.filter(primary__club=primary_club)

        # Filter by club_id (clubs contains club_id)
        club_id = self.kwargs.get("club_id", None)
        self.queryset = models.Event.objects.filter(clubs__id=club_id)

        # Filter by tag (tags contains tag)
        tag = self.kwargs.get("tag", None)
        self.queryset = models.Event.objects.filter(tags__name=tag)

        return super().get_queryset()


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
