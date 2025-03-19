from core.mock.models import Buster, BusterTag
from querycsv.serializers import CsvModelSerializer, WritableSlugRelatedField


class BusterTagNestedSerializer(CsvModelSerializer):
    """Serializer for testing nested fields."""

    class Meta(CsvModelSerializer.Meta):
        model = BusterTag
        fields = [
            "id",
            "name",
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

    class Meta(CsvModelSerializer.Meta):
        model = Buster
        fields = [
            "id",
            "created_at",
            "updated_at",
            "name",
            "unique_name",
            "one_tag_nested",
            "one_tag_str",
            "many_tags_nested",
            "many_tags_str",
            "many_tags_int",
        ]
        exclude = None

    # def create(self, validated_data):
    #     many_tags_nested = validated_data.pop("many_tags", [])
    #     one_tag_nested = validated_data.pop("one_tag", None)

    #     print("validated data:", validated_data)

    #     buster: Buster = super().create(validated_data)

    #     for tag in many_tags_nested:
    #         buster.many_tags.add(BusterTag.objects.create(**tag))

    #     if one_tag_nested:
    #         buster.one_tag = BusterTag.objects.create(**one_tag_nested)

    #     buster.save()
    #     return buster
