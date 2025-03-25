from core.abstracts.viewsets import ModelViewSetBase

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
