"""
Serializers for the analytics API View
"""

from rest_framework import serializers

from clubs.models import Club, ClubMembership, ClubRole, Team, TeamMembership
from core.abstracts.serializers import ImageUrlField, ModelSerializerBase
from querycsv.serializers import CsvModelSerializer
from analytics.models import Link, LinkManager, LinkVisit, QRCode
from django.shortcuts import get_object_or_404

class LinkClubNestedSerializer(serializers.ModelSerializer):
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

class LinkSerializer(serializers.ModelSerializer): 
    """Represents link info"""

    target_url = serializers.CharField(required=True)
    display_name = serializers.CharField(allow_null=True, allow_blank=True)

    club = LinkClubNestedSerializer(
        many=False, read_only=True
    )

    club_id = serializers.IntegerField(write_only=True, required=True)

    link_visits = serializers.IntegerField(read_only=True)
    

    class Meta:
        model = Link
        fields = [
            "id",
            "target_url",
            "display_name",
            "club",
            "club_id",
            "link_visits",
        ]

    def create(self, validated_data):
        club_id = validated_data.pop("club_id")
        club = get_object_or_404(Club, id=club_id)
        link = Link.objects.create(club=club, **validated_data)
        return link
    
