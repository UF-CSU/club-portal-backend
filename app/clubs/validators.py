from django.core.validators import MinValueValidator
from rest_framework import serializers


class ClubPreviewRetrieveValidator(serializers.Serializer):
    pk = serializers.IntegerField(validators=[MinValueValidator(1)])

    class Meta:
        fields = "__all__"


class ClubPreviewListValidator(serializers.Serializer):
    limit = serializers.IntegerField(
        allow_null=True, required=False, default=None, validators=[MinValueValidator(1)]
    )
    offset = serializers.IntegerField(
        allow_null=True, required=False, default=None, validators=[MinValueValidator(0)]
    )
    is_csu_partner = serializers.BooleanField(
        allow_null=True, required=False, default=None, validators=[]
    )

    class Meta:
        fields = "__all__"
