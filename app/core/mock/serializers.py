from core.abstracts.serializers import ImageUrlField
from core.mock.models import Buster, BusterTag
from querycsv.serializers import CsvModelSerializer, WritableSlugRelatedField


class BusterTagNestedSerializer(CsvModelSerializer):
    """Serializer for testing nested fields."""

    class Meta(CsvModelSerializer.Meta):
        model = BusterTag
        fields = [
            "id",
            "name",
            "color",
        ]


class BusterCsvSerializer(CsvModelSerializer):
    """Serialize dummy model for testing."""

    many_tags_int = WritableSlugRelatedField(
        source="many_tags",
        slug_field="id",
        queryset=BusterTag.objects.all(),
        many=True,
        required=False,
        allow_null=True,
    )
    many_tags_str = WritableSlugRelatedField(
        slug_field="name",
        source="many_tags",
        queryset=BusterTag.objects.all(),
        many=True,
        required=False,
        allow_null=True,
    )
    many_tags_nested = BusterTagNestedSerializer(
        many=True,
        required=False,
        source="many_tags",
    )

    one_tag_str = WritableSlugRelatedField(
        slug_field="name",
        source="one_tag",
        required=False,
        queryset=BusterTag.objects.all(),
        allow_null=True,
    )
    one_tag_nested = BusterTagNestedSerializer(
        allow_null=True, required=False, source="one_tag"
    )

    image = ImageUrlField(required=False)

    class Meta(CsvModelSerializer.Meta):
        model = Buster
        fields = [
            "id",
            "created_at",
            "updated_at",
            "name",
            "unique_name",
            "unique_email",
            "image",
            "one_tag_nested",
            "one_tag_str",
            "many_tags_nested",
            "many_tags_str",
            "many_tags_int",
        ]
        exclude = None
