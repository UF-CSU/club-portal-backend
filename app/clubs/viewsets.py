from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework import exceptions, mixins, status
from rest_framework.generics import GenericAPIView
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from clubs.models import Club, ClubApiKey, ClubFile, ClubMembership, ClubTag, Team
from clubs.serializers import (
    ClubApiKeySerializer,
    ClubApiSecretSerializer,
    ClubFileSerializer,
    ClubMembershipCreateSerializer,
    ClubMembershipSerializer,
    ClubPreviewSerializer,
    ClubSerializer,
    ClubTagSerializer,
    InviteClubMemberSerializer,
    JoinClubsSerializer,
    TeamSerializer,
)
from clubs.services import ClubService
from core.abstracts.viewsets import (
    CustomLimitOffsetPagination,
    ModelViewSetBase,
    ObjectViewDetailsPermissions,
    ViewSetBase,
)
from users.models import User


def get_user_club_or_404(club_id: int, user: User):
    """Get club for user, or raise 404 error."""

    try:
        return Club.objects.get_for_user(club_id, user)
    except Club.DoesNotExist:
        raise exceptions.NotFound(
            detail="Club with id %s does not exist for user." % club_id
        )


class ClubNestedViewSetBase(ModelViewSetBase):
    """
    Represents objects that require a club id to query.
    """

    def check_permissions(self, request):
        # This runs before `get_queryset`, will short-circuit out if user
        # does not have a club membership

        club_id = int(self.kwargs.get("club_id"))
        self.club = get_user_club_or_404(club_id, self.request.user)

        super().check_permissions(request)

    def get_queryset(self):
        self.queryset = self.queryset.filter(club__id=self.club.id)

        return super().get_queryset()

    def perform_create(self, serializer, **kwargs):
        serializer.save(club=self.club, **kwargs)


class ClubViewSet(ModelViewSetBase):
    """CRUD Api routes for Club models."""

    serializer_class = ClubSerializer
    queryset = Club.objects.all()
    permission_classes = [*ViewSetBase.permission_classes, ObjectViewDetailsPermissions]

    def check_permissions(self, request):

        if self.detail:
            # Check if the user is a member of specified club
            club_id = int(self.kwargs.get("pk"))
            get_user_club_or_404(club_id, self.request.user)
        elif self.action == "list":
            # List permissions are done by queryset, otherwise users without a club
            # would get 403 instead of an empty list.
            return

        return super().check_permissions(request)

    def get_queryset(self):
        return Club.objects.filter_for_user(self.request.user)

    def filter_queryset(self, queryset):
        # Filter by whether user is admin
        is_admin = self.request.query_params.get("is_admin", None)

        if is_admin is not None:
            admin_clubs = list(
                self.request.user.club_memberships.filter_is_admin().values_list(
                    "club__id", flat=True
                )
            )
            queryset = queryset.filter(id__in=admin_clubs)

        # Filter by major
        majors = self.request.query_params.getlist("majors", None)

        if majors:
            queryset = queryset.filter(majors__name__in=majors)
        return super().filter_queryset(queryset)


class UserClubMembershipsViewSet(ModelViewSetBase):
    """API for managing a use's club memberships."""

    queryset = ClubMembership.objects.none()
    serializer_class = ClubMembershipSerializer

    def get_queryset(self):
        return ClubMembership.objects.filter(user=self.request.user)

    def check_object_permissions(self, request, obj):
        if request.user.id == obj.user.id:
            return True
        return super().check_object_permissions(request, obj)


class ClubPreviewViewSet(
    mixins.ListModelMixin, mixins.RetrieveModelMixin, GenericViewSet
):
    queryset = (
        Club.objects.all()
        .select_related("logo", "banner")
        .prefetch_related("tags", "socials")
    )
    serializer_class = ClubPreviewSerializer
    pagination_class = CustomLimitOffsetPagination


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
        context["club_id"] = self.kwargs.get("club_id")
        return context

    def get_serializer_class(self):
        if self.action == "create":
            return ClubMembershipCreateSerializer

        return super().get_serializer_class()

    def perform_update(self, serializer):
        instance: ClubMembership = serializer.instance
        user_membership = ClubMembership.objects.get(
            user=self.request.user, club=instance.club
        )

        # Check club ownership edge cases
        is_owner_value = serializer.validated_data.get("is_owner", None)
        if is_owner_value is not None:
            if not user_membership.is_owner:
                raise exceptions.PermissionDenied(
                    detail="Only owners can change ownership"
                )

            elif user_membership.is_owner and is_owner_value is False:
                raise exceptions.ParseError(
                    detail="Cannot unset ownership, must set to someone else"
                )

        return super().perform_update(serializer)

    def perform_destroy(self, instance):
        if instance.is_owner:
            raise exceptions.ParseError(detail="Cannot delete owner of club")
        return super().perform_destroy(instance)


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
    queryset = Team.objects.all().prefetch_related(
        "memberships",
        "memberships__user",
        "memberships__user__socials",
        "memberships__roles",
    )


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
