"""
Serializers for the user API View
"""

from django.contrib.auth import get_user_model
from rest_framework import serializers

from clubs.models import Club, ClubMembership, ClubRole, Team, TeamMembership
from core.abstracts.serializers import (
    ImageUrlField,
    ModelSerializer,
    ModelSerializerBase,
)
from querycsv.serializers import CsvModelSerializer
from users.models import Profile, SocialProfile, User


class UserClubNestedSerializer(ModelSerializerBase):
    """Represents nested club info for users."""

    id = serializers.IntegerField(source="club.id", read_only=True)
    name = serializers.CharField(source="club.name", read_only=True)
    # TODO: Add role, permissions

    class Meta:
        model = Club
        fields = [
            "id",
            "name",
        ]


class ProfileNestedSerializer(ModelSerializerBase):
    """Represent user profiles in api."""

    class Meta:
        model = Profile
        exclude = ["user", "created_at", "updated_at"]


class UserSerializer(ModelSerializer):
    """Represents a person in the system who can authenticate."""

    email = serializers.EmailField()
    username = serializers.CharField(required=False)
    clubs = UserClubNestedSerializer(
        source="club_memberships", many=True, required=False
    )
    profile = ProfileNestedSerializer(required=False)

    class Meta:
        model = get_user_model()
        fields = [
            *ModelSerializerBase.default_fields,
            "username",
            "email",
            "password",
            "clubs",
            "profile",
        ]
        # defines characteristics of specific fields
        extra_kwargs = {"password": {"write_only": True, "min_length": 5}}

    # override default create method to call custom create_user method
    def create(self, validated_data):
        """Cteate and return a user with encrypted password"""
        return get_user_model().objects.create_user(**validated_data)

    def update(self, instance, validated_data):  # override update method
        """Update and return user"""
        # instance: model instance being updated

        password = validated_data.pop(
            "password", None
        )  # get password from data, remove from dict. optional field
        user = super().update(instance, validated_data)  # users base update method

        if password:
            user.set_password(password)
            user.save()

        return user


class OauthDirectorySerializer(serializers.Serializer):
    """Display available OAuth api routes."""

    google = serializers.CharField()


class UserProfileNestedCsvSerialzier(CsvModelSerializer):
    """Manage user profiles for csv."""

    id = None
    created_at = None
    updated_at = None

    image = ImageUrlField(required=False)

    class Meta:
        model = Profile
        exclude = ["created_at", "updated_at", "user"]


class ClubMembershipNestedCsvSerializer(CsvModelSerializer):
    """Manage club memberships for user csvs."""

    club = serializers.SlugRelatedField(slug_field="name", queryset=Club.objects.all())
    roles = serializers.SlugRelatedField(
        slug_field="name", queryset=ClubRole.objects.all(), many=True, required=False
    )
    teams = serializers.SlugRelatedField(
        slug_field="name", queryset=Team.objects.all(), many=True, required=False
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if self.instance:
            self.fields["roles"].queryset = ClubRole.objects.filter(
                club=self.instance.club
            )
            self.fields["teams"].queryset = Team.objects.filter(club=self.instance.club)

    class Meta:
        model = ClubMembership
        fields = ["club", "roles", "teams"]

    def create(self, validated_data):
        teams = validated_data.pop("teams", [])

        membership: ClubMembership = super().create(validated_data)

        for team in teams:
            TeamMembership.objects.create(team=team, user=membership.user)

        return membership


class UserSocialNestedCsvSerializer(CsvModelSerializer):
    """Manage user social profiles in a csv."""

    class Meta:
        model = SocialProfile
        fields = ["username", "social_type", "url"]


class UserCsvSerializer(CsvModelSerializer):
    """Define fields in a csv for users."""

    profile = UserProfileNestedCsvSerialzier(required=False)
    club_memberships = ClubMembershipNestedCsvSerializer(many=True, required=False)
    socials = UserSocialNestedCsvSerializer(many=True, required=False)

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "email",
            "is_active",
            "is_staff",
            "profile",
            "club_memberships",
            "socials",
        ]
