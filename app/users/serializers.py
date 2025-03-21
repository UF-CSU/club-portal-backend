"""
Serializers for the user API View
"""

from django.contrib.auth import get_user_model
from rest_framework import serializers

from clubs.models import Club
from core.abstracts.serializers import ModelSerializerBase


class UserClubNestedSerializer(serializers.ModelSerializer):
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


class UserSerializer(ModelSerializerBase):
    """Serialzier for the user object."""

    email = serializers.EmailField()
    username = serializers.CharField(required=False)
    first_name = serializers.CharField(required=False)
    last_name = serializers.CharField(required=False)
    clubs = UserClubNestedSerializer(
        source="club_memberships", many=True, required=False
    )

    class Meta:
        model = get_user_model()
        fields = [
            *ModelSerializerBase.default_fields,
            "username",
            "email",
            "first_name",
            "last_name",
            "password",
            "clubs",
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
