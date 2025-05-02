from rest_framework import status
from rest_framework.response import Response

from core.abstracts.viewsets import ModelViewSetBase
from events.models import Event, EventCancellation

from . import models, serializers


class EventViewset(ModelViewSetBase):
    """CRUD Api routes for Event models."""

    queryset = models.Event.objects.all()
    serializer_class = serializers.EventSerializer

    def get_queryset(self):

        user_clubs = list(self.request.user.clubs.values_list("id", flat=True))
        return self.queryset.filter(clubs__id__in=user_clubs)


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
