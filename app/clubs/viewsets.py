from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.generics import GenericAPIView
from rest_framework.response import Response

from clubs.models import Club, ClubMembership
from clubs.serializers import (
    ClubMembershipSerializer,
    ClubSerializer,
    InviteClubMemberSerializer,
)
from clubs.services import ClubService
from core.abstracts.viewsets import ModelViewSetBase, ViewSetBase


class ClubViewSet(ModelViewSetBase):
    """CRUD Api routes for Club models."""

    serializer_class = ClubSerializer
    queryset = Club.objects.all()


class ClubMembershipViewSet(ModelViewSetBase):
    """CRUD Api routes for ClubMembership for a specific Club."""

    serializer_class = ClubMembershipSerializer
    queryset = ClubMembership.objects.all()

    def get_queryset(self):
        club_id = self.kwargs.get("club_id", None)
        self.queryset = ClubMembership.objects.filter(club__id=club_id)

        return super().get_queryset()

    def perform_create(self, serializer: ClubMembershipSerializer):
        club_id = self.kwargs.get("club_id", None)
        club = Club.objects.get(id=club_id)

        serializer.save(club=club)


class InviteClubMemberView(GenericAPIView):
    """Creates a POST route for inviting club members."""

    serializer_class = InviteClubMemberSerializer
    authentication_classes = ViewSetBase.authentication_classes
    permission_classes = ViewSetBase.permission_classes

    @extend_schema(responses={202: None})
    def post(self, request, id: int, *args, **kwargs):
        club = get_object_or_404(Club, id=id)
        serializer = self.serializer_class(data=request.POST)
        serializer.is_valid(raise_exception=True)

        emails = serializer.data.get("emails", [])

        ClubService(club).send_email_invite(emails)

        return Response(status=status.HTTP_202_ACCEPTED)
