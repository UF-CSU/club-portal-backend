from rest_framework import serializers
from rest_framework.fields import empty

from clubs.models import (
    Club,
    ClubApiKey,
    ClubMembership,
    ClubPhoto,
    ClubRole,
    ClubSocialProfile,
    ClubTag,
    Team,
    TeamMembership,
    TeamRole,
)
from clubs.services import ClubService
from core.abstracts.serializers import (
    ImageUrlField,
    ModelSerializerBase,
    PermissionRelatedField,
    SerializerBase,
)
from querycsv.serializers import CsvModelSerializer, WritableSlugRelatedField
from users.models import User
from users.services import UserService


class ClubMemberNestedSerializer(ModelSerializerBase):
    """Represents a user's membership within a club."""

    user_id = serializers.IntegerField(source="user.id", read_only=True)
    username = serializers.CharField(source="user.username", read_only=True)
    is_owner = serializers.BooleanField(read_only=True)
    roles = serializers.SlugRelatedField(
        slug_field="name",
        many=True,
        queryset=ClubRole.objects.all(),  # TODO: Restrict roles to club only
        required=False,
    )

    class Meta:
        model = ClubMembership
        fields = [
            *ModelSerializerBase.default_fields,
            "user_id",
            "username",
            "is_owner",
            "points",
            "roles",
        ]


class ClubPhotoNestedSerializer(ModelSerializerBase):
    """Represents photos for clubs."""

    class Meta:
        model = ClubPhoto
        fields = [*ModelSerializerBase.default_fields, "id", "photo", "order"]


class ClubSocialNestedSerializer(ModelSerializerBase):
    """Represents social profiles for clubs."""

    class Meta:
        model = ClubSocialProfile
        fields = ["id", "url", "username", "social_type", "order"]


class ClubSerializer(ModelSerializerBase):
    """Represents a Club object with all fields."""

    members = ClubMemberNestedSerializer(
        many=True, read_only=True, help_text="List of club members"
    )
    photos = ClubPhotoNestedSerializer(many=True, read_only=True)
    socials = ClubSocialNestedSerializer(many=True, read_only=True)
    # tags = ClubTagNestedSerializer(many=True, read_only=True)
    # teams = ClubTeamNestedSerializer(many=True, read_only=True)

    class Meta:
        model = Club
        fields = [
            *ModelSerializerBase.default_fields,
            "name",
            "logo",
            "banner",
            "about",
            "founding_year",
            "contact_email",
            # "tags",
            "members",
            # "teams",
            "socials",
            "photos",
            "alias",
        ]


class ClubMemberUserNestedSerializer(ModelSerializerBase):
    id = serializers.IntegerField(required=False, read_only=True)
    email = serializers.EmailField(
        required=True,
    )
    send_account_email = serializers.BooleanField(
        default=True,
        write_only=True,
        help_text="Send account setup email if user is being created for the first time",
    )
    account_setup_url = serializers.URLField(
        required=False,
        write_only=True,
        help_text="A new user will click a link in their email that will redirect to this url.",
    )

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "username",
            "name",
            "send_account_email",
            "account_setup_url",
        ]
        read_only_fields = ["id", "username", "name"]

    def validate(self, data):
        email = data.get("email")
        send_account_email = data.pop("send_account_email", True)
        account_setup_url = data.pop("account_setup_url", None)

        user, created = User.objects.get_or_create(email=email)

        if created and send_account_email:
            UserService(user).send_account_setup_link(next_url=account_setup_url)

        return user


class ClubMemberTeamNestedSerializer(ModelSerializerBase):
    """Display a user's team memberships with the club memberships api."""

    roles = serializers.SlugRelatedField(
        slug_field="name",
        many=True,
        queryset=TeamRole.objects.all(),  # TODO: Restrict roles to team only
    )

    class Meta:
        model = TeamMembership
        fields = [
            "id",
            "team",
            "roles",
        ]


class ClubMembershipSerializer(ModelSerializerBase):
    """Connects a User to a Club with some additional fields."""

    user = ClubMemberUserNestedSerializer()
    club_id = serializers.SlugRelatedField(
        slug_field="id", source="club", read_only=True
    )
    send_email = serializers.BooleanField(
        default=False, write_only=True, required=False
    )

    club_redirect_url = serializers.URLField(
        required=False,
        write_only=True,
        help_text="If the user has an existing account, they will redirect to this url.",
    )
    team_memberships = ClubMemberTeamNestedSerializer(many=True, required=False)
    roles = serializers.SlugRelatedField(
        slug_field="name",
        many=True,
        queryset=ClubRole.objects.all(),  # TODO: Restrict roles to club only
        required=False,
    )

    class Meta:
        model = ClubMembership
        fields = [
            *ModelSerializerBase.default_fields,
            "user",
            "club_id",
            "is_owner",
            "points",
            "club_redirect_url",
            "send_email",
            "is_admin",
            "team_memberships",
            "roles",
        ]

    def create(self, validated_data):
        club = validated_data.pop("club")

        membership = ClubService(club).add_member(**validated_data, fail_silently=False)

        return membership


class UserNestedSerializer(ModelSerializerBase):
    """Display a user within memberships."""

    id = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all()
    )  # TODO: Restrict users to club members only

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "email",
            "name",
        ]
        read_only_fields = ["username", "email", "name"]


class TeamMemberNestedSerializer(ModelSerializerBase):
    """List members of a specific team."""

    user = UserNestedSerializer()
    roles = serializers.SlugRelatedField(
        slug_field="name",
        many=True,
        queryset=TeamRole.objects.all(),  # TODO: Restrict roles to team only
    )

    class Meta:
        model = TeamMembership
        exclude = [
            "team",
        ]


class TeamSerializer(ModelSerializerBase):
    """Represents a sub group of users within a club."""

    memberships = TeamMemberNestedSerializer(many=True, required=False)

    class Meta:
        model = Team
        exclude = [
            "club",
        ]


class ClubApiKeySerializer(ModelSerializerBase):
    """Display club api tokens in api."""

    permissions = PermissionRelatedField(many=True)
    club_id = serializers.PrimaryKeyRelatedField(source="club", read_only=True)

    class Meta:
        model = ClubApiKey
        fields = [
            "id",
            "club_id",
            "name",
            "description",
            "permissions",
        ]

    def create(self, validated_data):
        club = validated_data.pop("club")

        return ClubApiKey.objects.create(club, **validated_data)


class ClubApiSecretSerializer(ClubApiKeySerializer):
    """Extend the club api key serializer to also provide a secret."""

    class Meta(ClubApiKeySerializer.Meta):
        fields = ClubApiKeySerializer.Meta.fields + ["secret"]


class JoinClubsSerializer(SerializerBase):
    """Allow authenticated user to join multiple clubs."""

    clubs = serializers.ListField(
        child=serializers.PrimaryKeyRelatedField(queryset=Club.objects.all())
    )


##############################################################
# MARK: CSV SERIALIZERS
##############################################################


class ClubSocialNestedCsvSerializer(CsvModelSerializer, ClubSocialNestedSerializer):
    """Represents a club's social accounts in a csv."""


class UserNestedCsvSerializer(CsvModelSerializer, UserNestedSerializer):
    """Represents a user in a csv."""

    id = serializers.CharField(required=False)
    email = serializers.EmailField(required=True)
    username = serializers.CharField(required=False)
    name = serializers.CharField(required=False)

    class Meta:
        model = User
        fields = ["id", "email", "username", "name"]


class ClubMembershipCsvSerializer(CsvModelSerializer, ClubMembershipSerializer):
    """Serialize club memberships for a csv."""

    user = UserNestedCsvSerializer(required=True)

    roles = WritableSlugRelatedField(
        slug_field="name",
        queryset=ClubRole.objects.none(),
        many=True,
        required=False,
    )

    def __init__(self, instance=None, data=empty, **kwargs):
        super(ClubMembershipCsvSerializer, self).__init__(instance, data, **kwargs)
        self.club = None

        if instance is not None:
            self.club = instance.club

        elif data is not empty:
            self.club = data.get("club", None)

        if self.club is None:
            return

        if isinstance(self.club, int) or isinstance(self.club, str):
            self.club = Club.objects.get(id=self.club)

        # Restrict roles queryset to only include current club
        self.fields["roles"].child_relation.queryset = ClubRole.objects.filter(
            club__id=self.club.id
        )

        # Used to get or create a new role
        self.fields["roles"].child_relation.extra_kwargs = {"club": self.club}

    class Meta:
        model = ClubMembership
        fields = [
            *ModelSerializerBase.default_fields,
            "club",
            "points",
            "roles",
            "user",
        ]

    def create(self, validated_data):
        # Manually create an roles if necessary
        roles = validated_data.pop("roles", [])
        club = validated_data.get("club")
        validated_data["roles"] = []

        for role in roles:
            if isinstance(role, ClubRole):
                validated_data["roles"].append(role)
                continue

            if not ClubRole.objects.filter(name=role, club=club).exists():
                validated_data["roles"].append(
                    ClubRole.objects.create(name=role, club=club)
                )

        return super().create(validated_data)


class InviteClubMemberSerializer(serializers.Serializer):
    """Define REST API fields for sending invites to new club members."""

    emails = serializers.ListField(child=serializers.EmailField())


class ClubCsvSerializer(CsvModelSerializer):
    """Represents clubs in csvs."""

    socials = ClubSocialNestedCsvSerializer(many=True, required=False)
    logo = ImageUrlField(required=False)
    tags = WritableSlugRelatedField(
        many=True, slug_field="name", queryset=ClubTag.objects.all(), required=False
    )

    class Meta:
        model = Club
        fields = "__all__"


class TeamMemberNestedCsvSerializer(CsvModelSerializer):
    """Represents team memberships in csvs."""

    roles = serializers.SlugRelatedField(
        slug_field="name", queryset=TeamRole.objects.none(), many=True, required=False
    )
    user = serializers.SlugRelatedField(
        slug_field="email", queryset=User.objects.all(), help_text="User's email"
    )

    class Meta:
        model = TeamMembership
        fields = ["id", "user", "roles"]


class TeamCsvSerializer(CsvModelSerializer):
    """Represent teams in csvs."""

    club = serializers.SlugRelatedField(slug_field="name", queryset=Club.objects.all())
    members = TeamMemberNestedCsvSerializer(
        many=True, required=False, source="memberships"
    )

    class Meta:
        model = Team
        fields = "__all__"

    def initialize_instance(self, data=None):
        super().initialize_instance(data)

        # This serializer will never run .create(), instead it will
        # always update since nested roles are dependent on a team existing.
        # To achieve this, an instance is created here before validation.
        if not self.instance:
            # Only need name and club, other fields will be applied at update
            club = self.get_fields()["club"].to_internal_value(data.get("club"))
            name = data.get("name")

            # Run a quick validation check before creating team
            self.run_validators({"name": name, "club": club})

            # Then manually set the instance to the new team
            self.instance = Team.objects.create(name=name, club=club)

        members = data.get("members", [])
        roles = set()

        for member in members:
            mem_roles = member.get("roles", [])
            roles.update(mem_roles)

        for role in roles:
            TeamRole.objects.get_or_create(team=self.instance, name=role)

        self.fields["members"].child.fields["roles"].child_relation.queryset = (
            TeamRole.objects.filter(team=self.instance)
        )
