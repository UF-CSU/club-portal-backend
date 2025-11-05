"""
Serializers for the analytics API View
"""

from clubs.models import Club
from django.shortcuts import get_object_or_404
from rest_framework import serializers

from analytics.models import Link, QRCode


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
    club = LinkClubNestedSerializer(many=False, read_only=True)
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
            "url",
        ]

    def create(self, validated_data):
        club_id = validated_data.pop("club_id")
        club = get_object_or_404(Club, id=club_id)
        link = Link.objects.create(club=club, **validated_data)
        return link


class QrLinkNestedSerializer(serializers.ModelSerializer):
    """Represents Nested links within QR info"""

    id = serializers.IntegerField(source="link.id", read_only=True)
    target_url = serializers.CharField(source="club.name", read_only=True)

    class Meta:
        model = Club
        fields = [
            "id",
            "target_url",
        ]


class QrSerializer(serializers.ModelSerializer):
    """Represents QR info"""

    link = QrLinkNestedSerializer(many=False, read_only=True)
    link_id = serializers.IntegerField(write_only=True, required=True)

    image = serializers.ImageField(required=False, allow_null=True)

    url = serializers.SerializerMethodField(read_only=True)
    width = serializers.SerializerMethodField(read_only=True)
    size = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = QRCode
        # Expose only the fields you want. Exclude any internals like qrcode_upload_path.
        fields = [
            "link_id",
            "link",
            "image",
            "url",
            "size",
            "width",
        ]

    def get_url(self, obj) -> str:
        # Assumes QRCode.url property returns the tracking URL
        try:
            return obj.url
        except Exception:
            return None

    def get_width(self, obj) -> int:
        try:
            return obj.width
        except Exception:
            return None

    def get_size(self, obj) -> str:
        try:
            return obj.size
        except Exception:
            return None

    def create(self, validated_data):
        link_id = validated_data.pop("link_id")

        image = validated_data.pop("image", None)

        link = get_object_or_404(Link, pk=link_id)
        qrcode = QRCode.objects.create(link=link)

        if image is not None:
            qrcode.image = image
        else:
            # Example: auto-generate QR image if you prefer.
            # from django.core.files.base import ContentFile
            # import io, qrcode
            # tracking_url = link.tracking_url
            # qr_img = qrcode.QRCode(...)
            # ... generate into buffer ...
            # qr.image.save(filename, ContentFile(buffer.read()), save=False)
            pass

        qrcode.save()

        return qrcode
