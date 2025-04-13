from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.generics import GenericAPIView
from rest_framework.response import Response

from clubs.models import Club, ClubApiKey, ClubMembership, Team
from clubs.serializers import (
    ClubApiKeySerializer,
    ClubApiSecretSerializer,
    ClubMembershipSerializer,
    ClubSerializer,
    InviteClubMemberSerializer,
    TeamSerializer,
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


class TeamViewSet(ModelViewSetBase):
    """CRUD Api routes for Team objects."""

    serializer_class = TeamSerializer
    queryset = Team.objects.all()

    def get_queryset(self):
        club_id = self.kwargs.get("club_id", None)
        self.queryset = Team.objects.filter(club__id=club_id)

        return super().get_queryset()

    def perform_create(self, serializer: TeamSerializer):
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


class ClubApiKeyViewSet(ModelViewSetBase):
    """Api routes for managing club api keys."""

    serializer_class = ClubApiKeySerializer
    queryset = ClubApiKey.objects.none()

    def get_queryset(self):
        club_id = self.kwargs.get("club_id")
        self.queryset = ClubApiKey.objects.filter(club__id=club_id)

        return super().get_queryset()

    def perform_create(self, serializer):
        club_id = self.kwargs.get("club_id", None)
        club = Club.objects.get(id=club_id)

        serializer.save(club=club)

    def get_serializer_class(self):
        # When the key is being created, allow users to see the secret
        if self.action == "create":
            return ClubApiSecretSerializer

        # Otherwise, the secret should not be visible
        return super().get_serializer_class()
