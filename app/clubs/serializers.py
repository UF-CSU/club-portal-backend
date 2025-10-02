from rest_framework import serializers
from rest_framework.fields import empty

from clubs.models import (
    Club,
    ClubApiKey,
    ClubFile,
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
from core.models import Major
from querycsv.serializers import CsvModelSerializer, WritableSlugRelatedField
from users.models import SocialProfile, User
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
            "is_admin",
            "is_viewer",
            "points",
            "roles",
            "is_pinned",
        ]


class ClubFileSerializer(ModelSerializerBase):
    """Represents a file that was uploaded to a club's media library."""

    file = serializers.FileField(
        help_text="Full url to file, upload multipart form file data to create/update",
    )

    class Meta:
        model = ClubFile
        fields = [
            "id",
            "club",
            "display_name",
            "file",
            "size",
            "uploaded_by",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "club",
            "uploaded_by",
            "size",
            "created_at",
            "updated_at",
        ]


class ClubFileNestedSerializer(ModelSerializerBase):
    """Display minimal info about a file."""

    id = serializers.IntegerField()

    class Meta:
        model = ClubFile
        fields = ["id", "display_name", "url", "size"]
        read_only_fields = ["display_name", "url", "size"]


class ClubPhotoSerializer(ModelSerializerBase):
    """Represents photos for clubs."""

    file = ClubFileNestedSerializer()

    class Meta:
        model = ClubPhoto
        fields = ["id", "file", "order"]


class ClubSocialSerializer(ModelSerializerBase):
    """Represents social profiles for clubs."""

    class Meta:
        model = ClubSocialProfile
        fields = ["id", "url", "username", "social_type", "order"]


class ClubTagSerializer(ModelSerializerBase):
    """Represents tags for clubs."""

    class Meta:
        model = ClubTag
        fields = ["id", "name", "color", "order"]


class ClubRoleSerializer(ModelSerializerBase):
    """Represents a group of permissions users can have in a club."""

    class Meta:
        model = ClubRole
        fields = ["id", "name", "is_default", "order", "role_type"]


class ClubSerializer(ModelSerializerBase):
    """Represents a Club object with all fields."""

    logo = ClubFileNestedSerializer()
    banner = ClubFileNestedSerializer(required=False, allow_null=True)
    photos = ClubPhotoSerializer(many=True)
    socials = ClubSocialSerializer(many=True)
    tags = ClubTagSerializer(many=True)
    majors = serializers.SlugRelatedField(
        slug_field="name",
        queryset=Major.objects.all(),
        required=False,
        many=True,
    )
    roles = ClubRoleSerializer(many=True, required=False)
    # roles = serializers.SlugRelatedField(
    #     many=True, slug_field="name", queryset=ClubRole.objects.all()
    # )
    # user_membership = ClubMemberNestedSerializer(
    #     required=False,
    # )

    member_count = serializers.IntegerField(read_only=True)

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
            "tags",
            "member_count",
            "socials",
            "photos",
            "alias",
            "majors",
            "primary_color",
            "text_color",
            "default_role",
            "roles",
            # "user_membership",
        ]

    def update(self, instance, validated_data):
        logo_data = validated_data.pop("logo", None)
        banner_data = validated_data.pop("banner", None)
        socials_data = validated_data.pop("socials", [])
        tags_data = validated_data.pop("tags", [])
        photos_data = validated_data.pop("photos", [])

        club = super().update(instance, validated_data)

        if logo_data:
            club.logo_id = logo_data["id"]
        if banner_data:
            club.banner_id = banner_data["id"]
        club.save()

        club.socials.all().delete()
        if socials_data:
            for social in socials_data:
                club.socials.create(**social)

        if tags_data:
            tag_names = [tag["name"] for tag in tags_data]
            tag_objects = ClubTag.objects.filter(name__in=tag_names)
            club.tags.set(tag_objects)

        club.photos.all().delete()
        if photos_data:
            for photo in photos_data:
                club.photos.create(file_id=photo["file"]["id"], order=photo["order"])

        return club


class ClubPreviewSerializer(ModelSerializerBase):
    """Preview club info for unauthorized users"""

    logo = ClubFileNestedSerializer()
    # banner = ClubFileNestedSerializer(required=False)
    tags = ClubTagSerializer(many=True, read_only=True)
    socials = ClubSocialSerializer(many=True, read_only=True)
    majors = serializers.SlugRelatedField(many=True, slug_field="name", read_only=True)

    class Meta:
        model = Club
        fields = [
            "id",
            "gatorconnect_url",
            "gatorconnect_organization_url",
            "name",
            "logo",
            "founding_year",
            "tags",
            "alias",
            "socials",
            "instagram_followers",
            "about",
            "member_count",
            "is_csu_partner",
            "is_claimed",
            "majors",
        ]


class ClubUserSocialsSerializer(ModelSerializerBase):
    """Show socials for a club member."""

    class Meta:
        model = SocialProfile
        fields = ["id", "social_type", "url"]
        read_only_fields = ["social_type", "url"]


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
    image = serializers.ImageField(source="profile.image", required=False)
    socials = ClubUserSocialsSerializer(many=True, read_only=True)

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "username",
            "name",
            "send_account_email",
            "account_setup_url",
            "image",
            "socials",
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
    """Connects a User to a Club, stores membership information for that user."""

    user = ClubMemberUserNestedSerializer()
    club_id = serializers.PrimaryKeyRelatedField(source="club", read_only=True)
    team_memberships = ClubMemberTeamNestedSerializer(many=True, required=False)
    roles = serializers.SlugRelatedField(
        slug_field="name",
        many=True,
        queryset=ClubRole.objects.none(),
        required=False,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not hasattr(self, "context") or not self.context:
            return
        club_id = self.context.get("club_id")
        if club_id:
            filtered_roles = ClubRole.objects.filter(club_id=club_id)
            self.fields["roles"].queryset = filtered_roles
            if hasattr(self.fields["roles"], "child_relation"):
                self.fields["roles"].child_relation.queryset = filtered_roles

    class Meta:
        model = ClubMembership
        fields = [
            *ModelSerializerBase.default_fields,
            "user",
            "club_id",
            "is_owner",
            "is_admin",
            "is_viewer",
            "points",
            "team_memberships",
            "roles",
            "is_pinned",
            "order",
        ]


class ClubMembershipCreateSerializer(ClubMembershipSerializer):
    """Connects a User to a Club, determines how memberships should be added."""

    send_email = serializers.BooleanField(
        default=False, write_only=True, required=False
    )
    club_redirect_url = serializers.URLField(
        required=False,
        write_only=True,
        help_text="If the user has an existing account, they will redirect to this url.",
    )

    class Meta(ClubMembershipSerializer.Meta):
        fields = [
            *ModelSerializerBase.default_fields,
            "user",
            "club_id",
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


class ClubUserNestedSerializer(ModelSerializerBase):
    """Display a user within memberships."""

    id = serializers.PrimaryKeyRelatedField(queryset=User.objects.all())
    image = serializers.ImageField(source="profile.image", required=False)
    socials = ClubUserSocialsSerializer(many=True, read_only=True)

    class Meta:
        model = User
        fields = ["id", "username", "email", "name", "image", "socials"]
        read_only_fields = ["username", "email", "name", "socials"]


class TeamMembershipSerializer(ModelSerializerBase):
    """List members of a specific team."""

    user = ClubUserNestedSerializer()
    roles = serializers.SlugRelatedField(
        slug_field="name",
        many=True,
        queryset=TeamRole.objects.all(),  # TODO: Restrict roles to team only
    )
    order = serializers.IntegerField(required=False)

    class Meta:
        model = TeamMembership
        exclude = [
            "team",
            "order_override",
        ]


class TeamSerializer(ModelSerializerBase):
    """Represents a sub group of users within a club."""

    memberships = TeamMembershipSerializer(many=True, required=False)

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


class ClubRosterSerializer(ModelSerializerBase):
    """Used to display a club's members."""

    executives = ClubMembershipSerializer(many=True)
    teams = TeamSerializer(many=True, source="roster_teams")

    class Meta:
        model = Club
        fields = ["executives", "teams"]


##############################################################
# MARK: CSV SERIALIZERS
##############################################################


class ClubSocialNestedCsvSerializer(CsvModelSerializer, ClubSocialSerializer):
    """Represents a club's social accounts in a csv."""


class UserNestedCsvSerializer(CsvModelSerializer, ClubUserNestedSerializer):
    """Represents a user in a csv."""

    id = serializers.CharField(required=False)
    email = serializers.EmailField(required=True)
    username = serializers.CharField(required=False)
    name = serializers.CharField(required=False)

    class Meta:
        model = User
        fields = ["id", "email", "username", "name"]


class ClubMembershipCsvSerializer(CsvModelSerializer, ClubMembershipCreateSerializer):
    """Serialize club memberships for a csv."""

    user = UserNestedCsvSerializer(required=True)

    roles = WritableSlugRelatedField(
        slug_field="name",
        queryset=ClubRole.objects.none(),
        many=True,
        required=False,
    )

    def __init__(self, instance=None, data=empty, **kwargs):
        super().__init__(instance, data, **kwargs)
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

    # def run_validation(self, data=dict):
    #     # logo = data.pop("logo", {})
    #     # print("validation logo:", logo)
    #     validated = super().run_validation(data)
    #     print("validated:", validated)

    #     return validated

    def create(self, validated_data):
        logo = validated_data.pop("logo", None)

        club = super().create(validated_data)

        if logo:
            file = ClubFile.objects.create(club=club, file=logo)
            club.logo = file
            club.save()

        return club

    def update(self, instance, validated_data):
        logo = validated_data.pop("logo", None)
        club = super().update(instance, validated_data)

        if logo and not club.logo.display_name == logo.name:
            file = ClubFile.objects.create(club=club, file=logo)
            club.logo = file
            club.save()

        return club


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

        self.fields["members"].child.fields[
            "roles"
        ].child_relation.queryset = TeamRole.objects.filter(team=self.instance)


class ClubRoleCsvSerializer(CsvModelSerializer):
    """Allow uploading/downloading club roles."""

    club = serializers.SlugRelatedField(slug_field="name", queryset=Club.objects.all())

    class Meta:
        model = ClubRole
        fields = "__all__"
