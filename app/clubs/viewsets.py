from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework import mixins, status
from rest_framework.generics import GenericAPIView
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from clubs.models import Club, ClubApiKey, ClubFile, ClubMembership, ClubTag, Team
from clubs.serializers import (
    ClubApiKeySerializer,
    ClubApiSecretSerializer,
    ClubFileSerializer,
    ClubMembershipSerializer,
    ClubPreviewSerializer,
    ClubSerializer,
    ClubTagSerializer,
    InviteClubMemberSerializer,
    JoinClubsSerializer,
    TeamSerializer,
)
from clubs.services import ClubService
from core.abstracts.viewsets import ModelViewSetBase, ViewSetBase


class ClubNestedViewSetBase(ModelViewSetBase):
    """
    Represents objects that require a club id to query.
    """

    def get_queryset(self):
        club_id = self.kwargs.get("club_id", None)
        self.queryset = self.queryset.filter(club__id=club_id)

        return super().get_queryset()

    def perform_create(self, serializer: ClubMembershipSerializer, **kwargs):
        club_id = self.kwargs.get("club_id", None)
        club = Club.objects.get(id=club_id)

        serializer.save(club=club, **kwargs)

    def check_permissions(self, request):
        club_id = self.kwargs.get("club_id", None)
        club = Club.objects.get(id=club_id)

        if not request.user.has_perm(
            "clubs.view_club", club
        ) or not request.user.has_perm("clubs.view_clubmembership", club):
            self.permission_denied(request)

        return super().check_permissions(request)


class ClubViewSet(ModelViewSetBase):
    """CRUD Api routes for Club models."""

    serializer_class = ClubSerializer
    queryset = Club.objects.all()

    def check_object_permissions(self, request, obj):
        if not request.user.has_perm("clubs.view_club", obj):
            self.permission_denied(request)

        return super().check_object_permissions(request, obj)

    def filter_queryset(self, queryset):
        qs = super().filter_queryset(queryset)

        has_membership = self.request.GET.get("has_membership", False)

        if has_membership:
            club_ids = self.request.user.clubs.values_list("id", flat=True)
            return qs.filter(id__in=club_ids)

        return qs

    def get_queryset(self):
        qs = super().get_queryset()

        request = self.request
        user = request.user

        if not user or not user.is_authenticated:
            if self.action == "list":
                return qs.none()
            else:
                self.permission_denied(self.request)

        if self.action == "list":
            return user.clubs.all()
        else:
            return qs


class ClubPreviewViewSet(
    mixins.ListModelMixin, mixins.RetrieveModelMixin, GenericViewSet
):
    queryset = Club.objects.all()
    serializer_class = ClubPreviewSerializer


class ClubTagsView(GenericAPIView):
    """Creates a GET route for fetching available club tags."""

    serializer_class = ClubTagSerializer
    authentication_classes = ViewSetBase.authentication_classes
    permission_classes = ViewSetBase.permission_classes

    def get(self, request):
        tags = ClubTag.objects.all().order_by("order", "name")
        serializer = self.serializer_class(tags, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class ClubMembershipViewSet(ClubNestedViewSetBase):
    """CRUD Api routes for ClubMembership for a specific Club."""

    serializer_class = ClubMembershipSerializer
    queryset = ClubMembership.objects.all()

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['club_id'] = self.kwargs.get('club_id')
        return context


class ClubMemberViewSet(
    ViewSetBase,
    mixins.RetrieveModelMixin,
):
    """CRUD Api routes for ClubMembership for a specific Club given specific User."""

    serializer_class = ClubMembershipSerializer
    queryset = ClubMembership.objects.all()

    lookup_field = "user_id"

    def get_object(self):
        club_id = self.kwargs.get("club_id", None)
        user_id = self.kwargs.get("user_id", None)

        if user_id is not None:
            try:
                user_id = int(user_id)
                club_id = int(club_id)
            except ValueError:

                return self.queryset.none()

        self.queryset = self.queryset.filter(club__id=club_id, user__id=user_id)

        return get_object_or_404(self.queryset)


class TeamViewSet(ClubNestedViewSetBase):
    """CRUD Api routes for Team objects."""

    serializer_class = TeamSerializer
    queryset = Team.objects.all()


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


class ClubApiKeyViewSet(ClubNestedViewSetBase):
    """Api routes for managing club api keys."""

    serializer_class = ClubApiKeySerializer
    queryset = ClubApiKey.objects.none()

    def get_serializer_class(self):
        # When the key is being created, allow users to see the secret
        if self.action == "create":
            return ClubApiSecretSerializer

        # Otherwise, the secret should not be visible
        return super().get_serializer_class()


class JoinClubsViewSet(GenericAPIView):
    """Allow authenticated user to join multiple clubs."""

    serializer_class = JoinClubsSerializer
    authentication_classes = ViewSetBase.authentication_classes
    permission_classes = []

    def post(self, request):
        """Submit request to join clubs."""

        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)

        clubs = serializer.validated_data.get("clubs")

        for club in clubs:
            ClubService(club).add_member(request.user)

        return Response(serializer.data)


class ClubFilesViewSet(ClubNestedViewSetBase):
    """Manage club files."""

    serializer_class = ClubFileSerializer
    queryset = ClubFile.objects.all()

    def perform_create(self, serializer, **kwargs):
        user = self.request.user
        return super().perform_create(serializer, uploaded_by=user, **kwargs)
