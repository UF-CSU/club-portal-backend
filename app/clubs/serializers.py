from clubs.models import (
    Club,
    ClubMembership,
    ClubRole,
    ClubSocialProfile,
    ClubTag,
    Team,
    TeamMembership,
    TeamRole,
)
from core.abstracts.serializers import ImageUrlField, ModelSerializerBase
from django.core import exceptions
from django.core.mail import send_mail
from querycsv.serializers import CsvModelSerializer, WritableSlugRelatedField
from rest_framework import serializers
from rest_framework.fields import empty
from users.models import User


class ClubMemberNestedSerializer(serializers.ModelSerializer):
    """Represents a user's membership within a club."""

    user_id = serializers.IntegerField(source="user.id", read_only=True)
    username = serializers.CharField(source="user.username", read_only=True)
    owner = serializers.BooleanField(read_only=True)

    class Meta:
        model = ClubMembership
        fields = [
            *ModelSerializerBase.default_fields,
            "user_id",
            "username",
            "owner",
            "points",
        ]


class ClubSocialNestedSerializer(CsvModelSerializer):
    """Represents social profiles for clubs."""

    class Meta:
        model = ClubSocialProfile
        fields = ["id", "url", "username", "social_type", "order"]


class ClubSerializer(ModelSerializerBase):
    """Convert club model to JSON fields."""

    members = ClubMemberNestedSerializer(many=True, read_only=True)
    socials = ClubSocialNestedSerializer(many=True, read_only=True)
    # tags = ClubTagNestedSerializer(many=True, read_only=True)
    # teams = ClubTeamNestedSerializer(many=True, read_only=True)

    class Meta:
        model = Club
        fields = [
            *ModelSerializerBase.default_fields,
            "name",
            "logo",
            "about",
            "founding_year",
            "contact_email",
            # "tags",
            "members",
            # "teams",
            "socials"
        ]


class ClubCsvSerializer(CsvModelSerializer):
    """Represents clubs in csvs."""

    socials = ClubSocialNestedSerializer(many=True, required=False)
    logo = ImageUrlField(required=False)
    tags = WritableSlugRelatedField(
        many=True, slug_field="name", queryset=ClubTag.objects.all(), required=False
    )

    class Meta:
        model = Club
        fields = "__all__"


class TeamMemberNestedCsvSerializer(CsvModelSerializer):
    """Represents team memberships in csvs."""

    roles = WritableSlugRelatedField(
        slug_field="name",
        queryset=TeamRole.objects.none(),
        many=True,
        required=False,
    )
    roles = serializers.SlugRelatedField(
        slug_field="name", queryset=TeamRole.objects.none(), many=True, required=False
    )
    user = serializers.SlugRelatedField(slug_field="email", queryset=User.objects.all())

    class Meta:
        model = TeamMembership
        fields = ["id", "user", "roles"]


class TeamCsvSerializer(CsvModelSerializer):
    """Represent teams in csvs."""

    club = serializers.SlugRelatedField(slug_field="name", queryset=Club.objects.all())
    memberships = TeamMemberNestedCsvSerializer(many=True, required=False)

    class Meta:
        model = Team
        fields = "__all__"


class ClubMembershipSerializer(ModelSerializerBase):
    """Represents a club membership to use for CRUD operations."""
    
    class UserSerializer(ModelSerializerBase):
        id = serializers.IntegerField(required=False)
        email = serializers.EmailField(required=False)
        
        def validate(self, data):
            id = data.get("id")
            email = data.get("email")
            
            # Validate user_id and user_email
            if id is None and email is None:
                raise exceptions.ValidationError(
                    "Either user_id or user_email is required!"
                )
            
            if id is not None and email is not None:
                raise exceptions.ValidationError(
                    "Either provide user_id or user_email, not both!"
                )
            
            if email is not None:
                user, created = User.objects.get_or_create(email=email)

                # New user was created, send an email to sign up
                if created:
                    # TODO: Update this to send_html_mail and fill out fields
                    send_mail(
                        subject="Finish Account Creation",
                        message=f"Finish creating your account...",
                        from_email="admin@example.com",
                        recipient_list=[email],
                    )
            else:
                user = User.objects.get_by_id(id)
            
            return user
        
        class Meta:
            model = User
            fields = ['id', 'email']

    user = UserSerializer()
    club_id = serializers.SlugRelatedField(
        slug_field="id", source="club", read_only=True
    )

    class Meta:
        model = ClubMembership
        fields = [
            *ModelSerializerBase.default_fields,
            "user",
            "club_id",
            "owner",
            "points",
        ]
    
    def create(self, validated_data):
        user = validated_data.get("user")
        club = validated_data.get("club")
        
        # Create membership
        membership = ClubMembership.objects.create(club=club, user=user)
        
        return membership

class ClubMembershipCsvSerializer(CsvModelSerializer, ClubMembershipSerializer):
    """Serialize club memberships for a csv."""

    # user_id = PrimaryKeyRelatedField(queryset=User.objects.all(), required=False)
    user_email = WritableSlugRelatedField(
        source="user", slug_field="email", queryset=User.objects.all(), required=True
    )
    user_id = serializers.CharField(source="user.id", required=False)
    user_username = serializers.CharField(source="user.username", required=False)

    # TODO: Allow csv to update user first and last name, likely need to implement as nested object
    user_first_name = serializers.CharField(source="user.first_name", required=False)
    user_last_name = serializers.CharField(source="user.last_name", required=False)

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
            "user_email",
            "user_id",
            "user_username",
            "user_first_name",
            "user_last_name",
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
