from core.abstracts.viewsets import (
    FilterBackendBase,
    ModelPreviewViewSetBase,
    ModelViewSetBase,
    ObjectViewDetailsPermissions,
    ViewSetBase,
)
from core.models import Major
from django.db.models import Count, Prefetch
from django.shortcuts import get_object_or_404
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django.views.decorators.vary import vary_on_headers
from drf_spectacular.utils import extend_schema
from rest_framework import exceptions, mixins, permissions, status
from rest_framework.decorators import action
from rest_framework.generics import GenericAPIView
from rest_framework.request import Request
from rest_framework.response import Response
from users.models import User
from utils.cache import check_cache, set_cache
from utils.views import params_validator, parse_bool_param

from clubs.cache import (
    DETAIL_CLUB_PREVIEW_PREFIX,
    LIST_CLUB_PREVIEW_PREFIX,
)
from clubs.models import (
    Club,
    ClubApiKey,
    ClubFile,
    ClubMembership,
    ClubRole,
    ClubSocialProfile,
    ClubTag,
    RoleType,
    Team,
    TeamMembership,
    TeamRole,
)
from clubs.serializers import (
    ClubApiKeySerializer,
    ClubApiSecretSerializer,
    ClubFileSerializer,
    ClubMemberSerializer,
    ClubMembershipCreateSerializer,
    ClubMembershipSerializer,
    ClubPreviewListParamSerializer,
    ClubPreviewSerializer,
    ClubRosterSerializer,
    ClubSerializer,
    ClubTagSerializer,
    InviteClubMemberSerializer,
    FollowClubsSerializer,
    JoinClubsSerializer,
    TeamSerializer,
)
from clubs.services import ClubService


def get_user_club_or_404(club_id: int, user: User):
    """Get club for user, or raise 404 error."""

    try:
        return Club.objects.get_for_user(club_id, user)

    except Club.DoesNotExist as e:
        raise exceptions.NotFound(
            detail="Club with id %s does not exist for user." % club_id
        ) from e


class ClubNestedViewSetBase(ModelViewSetBase):
    """
    Represents objects that require a club id to query.
    """

    # permission_classes = ModelViewSetBase.permission_classes + [
    #     permissions.IsAuthenticated
    # ]

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


class ClubQueryFilter(FilterBackendBase):
    """Filter by club."""

    filter_fields = [
        {"name": "club", "schema_type": "number", "description": "Club ID"}
    ]

    def filter_queryset(self, request, queryset, view):
        club_id = request.query_params.get("club", None)

        if not club_id:
            return queryset

        return queryset.filter(club__id=club_id)


class IsClubAdminFilter(FilterBackendBase):
    """Get clubs that a user is an admin of."""

    filter_fields = [{"name": "is_admin", "schema_type": "boolean"}]

    def filter_queryset(self, request, queryset, view):
        is_admin = request.query_params.get("is_admin", None)

        # When type conversion works and is_admin is a boolean, update the code
        if is_admin == "true":
            admin_clubs = list(
                request.user.club_memberships.filter_is_admin().values_list(
                    "club__id", flat=True
                )
            )
            queryset = queryset.filter(id__in=admin_clubs)

        elif is_admin == "false":
            member_clubs = list(
                request.user.club_memberships.filter_is_not_admin().values_list(
                    "club__id", flat=True
                )
            )
            queryset = queryset.filter(id__in=member_clubs)

        return queryset


class ClubViewSet(ModelViewSetBase):
    """CRUD Api routes for Club models."""

    serializer_class = ClubSerializer
    queryset = Club.objects.all()
    permission_classes = [*ViewSetBase.permission_classes, ObjectViewDetailsPermissions]
    filter_backends = [IsClubAdminFilter]

    def check_permissions(self, request):
        if self.detail:
            # Check if the user is a member of specified club
            club_id = int(self.kwargs.get("pk"))
            get_user_club_or_404(club_id, self.request.user)
        elif self.action == "list":
            # List permissions are done by queryset, otherwise users without a club
            # would get 403 instead of an empty list.
            if not request.user.is_anonymous:
                return

        return super().check_permissions(request)

    def get_queryset(self):
        return Club.objects.filter_for_user(self.request.user)

    def get_serializer_class(self):
        if self.action == "get_roster":
            return ClubRosterSerializer
        return super().get_serializer_class()

    @action(methods=["GET"], detail=True, url_name="roster", url_path="roster")
    def get_roster(self, request, pk=None, *args, **kwargs):
        club = get_object_or_404(self.get_queryset(), pk=pk)
        serializer = self.get_serializer_class()(club)
        return Response(serializer.data)


class UserClubMembershipsViewSet(ModelViewSetBase):
    """Manage club memberships that belong to the user."""

    queryset = ClubMembership.objects.select_related(
        "user",
    ).prefetch_related(
        Prefetch(
            "roles",
            queryset=ClubRole.objects.all().order_by("order"),
            to_attr="_prefetched_roles_cache",
        ),
        Prefetch(
            "user__team_memberships",
            queryset=TeamMembership.objects.select_related("team").prefetch_related(
                Prefetch(
                    "team__roles",
                    queryset=TeamRole.objects.order_by("order"),
                    to_attr="prefetched_roles",
                ),
            ),
            to_attr="prefetched_team_memberships",
        ),
    )
    serializer_class = ClubMembershipSerializer

    def get_serializer_context(self):
        context = super().get_serializer_context()
        if self.action == "list":
            context["skip_role_queryset"] = True

        context["club_id"] = self.kwargs.get("club_id")
        return context

    def get_queryset(self):
        return self.queryset.filter(user=self.request.user)

    def check_object_permissions(self, request, obj):
        if request.user.id == obj.user.id:
            return True
        return super().check_object_permissions(request, obj)


class ClubPreviewViewSet(ModelPreviewViewSetBase):
    """Access limited club data via the API."""

    queryset = (
        Club.objects.select_related("logo", "banner")
        .prefetch_related(
            Prefetch("tags", queryset=ClubTag.objects.order_by("order", "name")),
            Prefetch("majors", queryset=Major.objects.only("id", "name")),
            Prefetch("socials", queryset=ClubSocialProfile.objects.order_by("order")),
            Prefetch(
                "memberships",
                queryset=ClubMembership.objects.filter(is_owner=True).select_related(
                    "user"
                ),
                to_attr="prefetched_owner_memberships",
            ),
        )
        .annotate(member_count=Count("memberships", distinct=True))
    )
    serializer_class = ClubPreviewSerializer

    search_fields = ["name", "alias"]
    filterset_fields = ["is_csu_partner", "majors__name", "tags"]

    authentication_classes = []
    permission_classes = [permissions.AllowAny]

    def retrieve(self, request: Request, *args, **kwargs):
        club_id = self.kwargs.get("pk")
        result = check_cache(DETAIL_CLUB_PREVIEW_PREFIX, club_id=club_id)

        if not result:
            try:
                club = super().retrieve(request, *args, **kwargs).data
            except Club.DoesNotExist as e:
                raise exceptions.NotFound(f"No club found for id: {club_id}") from e

            result = ClubPreviewSerializer(club).data
            set_cache(result, DETAIL_CLUB_PREVIEW_PREFIX, club_id=club_id)

        return Response(result)

    @params_validator(
        ClubPreviewListParamSerializer,
        query_params=["limit", "offset", "is_csu_partner"],
    )
    def list(self, request: Request, *args, **kwargs):
        params = request.query_params.copy()
        limit = params.get("limit", None)
        offset = params.get("offset", None)
        is_csu_partner = parse_bool_param(
            params.get("is_csu_partner", None), "is_csu_partner"
        )

        result = check_cache(
            LIST_CLUB_PREVIEW_PREFIX,
            is_csu_partner=is_csu_partner,
            limit=limit,
            offset=offset,
        )
        if not result:
            result = super().list(request, *args, **kwargs).data

            set_cache(
                result,
                LIST_CLUB_PREVIEW_PREFIX,
                is_csu_partner=is_csu_partner,
                limit=limit,
                offset=offset,
            )

        return Response(result)


class ClubTagsView(GenericAPIView):
    """Creates a GET route for fetching available club tags."""

    serializer_class = ClubTagSerializer
    authentication_classes = ViewSetBase.authentication_classes
    permission_classes = ViewSetBase.permission_classes

    def get(self, request):
        tags = ClubTag.objects.all().order_by("order", "name")
        serializer = self.serializer_class(tags, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class ClubMemberViewSet(ClubNestedViewSetBase):
    """Manage members in a club."""

    serializer_class = ClubMemberSerializer
    queryset = ClubMembership.objects.select_related(
        "user", "user__profile"
    ).prefetch_related(
        "user__socials",
        Prefetch(
            "roles",
            queryset=ClubRole.objects.order_by("order"),
            to_attr="_prefetched_roles_cache",
        ),
        Prefetch(
            "user__team_memberships",
            queryset=TeamMembership.objects.select_related("team").prefetch_related(
                Prefetch(
                    "team__roles",
                    queryset=TeamRole.objects.order_by("order"),
                    to_attr="prefetched_roles",
                )
            ),
            to_attr="prefetched_team_memberships",
        ),
    )

    def get_serializer_context(self):
        context = super().get_serializer_context()
        if self.action == "list":
            context["skip_role_queryset"] = True
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


# TODO: Remove this in favor of ClubMembershipViewSet
class ClubMembershipSingleViewSet(
    ViewSetBase,
    mixins.RetrieveModelMixin,
):
    """CRUD Api routes for ClubMembership for a specific Club given specific User."""

    serializer_class = ClubMemberSerializer
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
    queryset = Team.objects.prefetch_related(
        Prefetch(
            "memberships",
            queryset=TeamMembership.objects.select_related("user").prefetch_related(
                "user__socials", "roles"
            ),
        )
    )

    # Cache detail view for 2 hours (per Authorization header)
    @method_decorator(cache_page(60 * 60 * 2))
    @method_decorator(vary_on_headers("Authorization"))
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    # Cache list view for 2 hours (per Authorization header)
    @method_decorator(cache_page(60 * 60 * 2))
    @method_decorator(vary_on_headers("Authorization"))
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)


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


class FollowClubsViewSet(GenericAPIView):
    """Allow authenticated user to follow multiple clubs with the Follower role."""

    serializer_class = FollowClubsSerializer
    authentication_classes = ViewSetBase.authentication_classes
    permission_classes = []

    def post(self, request):
        """Submit request to follow clubs."""

        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)

        clubs = serializer.validated_data.get("clubs")

        for club in clubs:
            already_member = ClubMembership.objects.filter(
                club=club, user=request.user
            ).exists()
            if already_member:
                continue

            follower_role = club.roles.filter(role_type=RoleType.FOLLOWER).first()
            roles = [follower_role] if follower_role else None

            ClubService(club).add_member(request.user, roles=roles)

        return Response(serializer.data)


class ClubFilesViewSet(ClubNestedViewSetBase):
    """Manage club files."""

    serializer_class = ClubFileSerializer
    queryset = ClubFile.objects.all()

    def perform_create(self, serializer, **kwargs):
        user = self.request.user
        return super().perform_create(serializer, uploaded_by=user, **kwargs)
