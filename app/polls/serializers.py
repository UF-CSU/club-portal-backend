"""
Convert poll models to json objects.
"""

from rest_framework import serializers

from core.abstracts.serializers import (
    ModelSerializer,
    ModelSerializerBase,
    StringListField,
)
from polls import models


class TextInputNestedSerializer(ModelSerializerBase):
    """Show text input in poll question json."""

    class Meta:
        model = models.TextInput
        fields = ["id", "text_type", "min_length", "max_length", "question"]
        extra_kwargs = {"question": {"required": False}}


class ChoiceInputOptionNestedSerializer(ModelSerializerBase):
    """Show choice input options in poll question json."""

    value = serializers.CharField(required=False)

    class Meta:
        model = models.ChoiceInputOption
        fields = ["id", "label", "value", "image", "order"]


class ChoiceInputNestedSerializer(ModelSerializerBase):
    """Show choice input in poll question json."""

    options = ChoiceInputOptionNestedSerializer(many=True)

    class Meta:
        model = models.ChoiceInput
        fields = ["id", "options", "question"]
        extra_kwargs = {"question": {"required": False}}


class RangeInputNestedSerializer(ModelSerializerBase):
    """Show range input in poll question json."""

    class Meta:
        model = models.RangeInput
        fields = [
            "id",
            "min_value",
            "max_value",
            "left_label",
            "right_label",
            "step",
            "initial_value",
            "unit",
            "question",
        ]
        extra_kwargs = {"question": {"required": False}}


class UploadInputNestedSerializer(ModelSerializerBase):
    """Show upload input in poll question json."""

    file_types = StringListField(required=False)

    class Meta:
        model = models.UploadInput
        fields = ["id", "file_types", "max_files", "question"]
        extra_kwargs = {"question": {"required": False}}


class NumberInputNestedSerializer(ModelSerializerBase):
    """Show number input in poll question json."""

    class Meta:
        model = models.NumberInput
        fields = [
            "id",
            "min_value",
            "max_value",
            "unit",
            "decimal_places",
            "question",
        ]
        extra_kwargs = {"question": {"required": False}}


class PollQuestionNestedSerializer(ModelSerializerBase):
    """Show questions nested in poll fields."""

    text_input = TextInputNestedSerializer(required=False)
    choice_input = ChoiceInputNestedSerializer(required=False)
    range_input = RangeInputNestedSerializer(required=False)
    upload_input = UploadInputNestedSerializer(required=False)
    number_input = NumberInputNestedSerializer(required=False)

    created_at = None
    updated_at = None

    class Meta:
        model = models.PollQuestion
        exclude = ["created_at", "updated_at"]
        extra_kwargs = {"field": {"required": False}}

    def create(self, validated_data):
        """Create question with nested inputs."""

        text_input = validated_data.pop("text_input", None)
        choice_input = validated_data.pop("choice_input", None)
        range_input = validated_data.pop("range_input", None)
        upload_input = validated_data.pop("upload_input", None)
        number_input = validated_data.pop("number_input", None)

        question = super().create(validated_data)

        if text_input:
            models.TextInput.objects.create(**text_input, question=question)

        if choice_input:
            options = choice_input.pop("options")
            choice_input = models.ChoiceInput.objects.create(
                **choice_input, question=question
            )

            for option in options:
                models.ChoiceInputOption.objects.create(input=choice_input, **option)

        if range_input:
            models.RangeInput.objects.create(**range_input, question=question)

        if upload_input:
            models.UploadInput.objects.create(**upload_input, question=question)

        if number_input:
            models.NumberInput.objects.create(**number_input, question=question)

        return question


class PollMarkupNestedSerializer(ModelSerializerBase):
    """Show markup in poll field json."""

    class Meta:
        model = models.PollMarkup
        fields = ["id", "content", "field"]
        extra_kwargs = {"field": {"required": False}}


class PollFieldNestedSerializer(ModelSerializerBase):
    """Show poll fields nested in polls."""

    question = PollQuestionNestedSerializer(required=False)
    markup = PollMarkupNestedSerializer(required=False)

    class Meta:
        model = models.PollField
        fields = ["id", "field_type", "order", "question", "markup"]


class PollSerializer(ModelSerializer):
    """JSON definition for polls."""

    fields = PollFieldNestedSerializer(many=True)

    class Meta:
        model = models.Poll
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at"]

    def create(self, validated_data):
        """Create poll with nested fields."""

        fields = validated_data.pop("fields")
        poll = super().create(validated_data)

        for field_data in fields:
            question = field_data.pop("question", None)
            markup = field_data.pop("markup", None)

            field = models.PollField.objects.create(poll=poll, **field_data)

            if question:
                serializer = PollQuestionNestedSerializer(
                    data={**question, "field": field.id}
                )
                serializer.is_valid(raise_exception=True)
                serializer.save()

            if markup:
                serializer = PollMarkupNestedSerializer(
                    data={**markup, "field": field.id}
                )
                serializer.is_valid(raise_exception=True)
                serializer.save()

        return poll


class PollSubmissionAnswerSerializer(ModelSerializerBase):
    """Record a user's answer for a specific question."""

    options_value = serializers.SlugRelatedField(
        many=True,
        required=False,
        slug_field="value",
        queryset=models.ChoiceInputOption.objects.all(),
    )

    class Meta:
        model = models.PollQuestionAnswer
        fields = [
            "id",
            "question",
            "text_value",
            "number_value",
            "options_value",
            "is_valid",
            "error",
            "created_at",
        ]


class PollSubmissionSerializer(ModelSerializer):
    """A user's submission for a form."""

    # Poll id is set in the url
    poll = serializers.PrimaryKeyRelatedField(read_only=True)
    answers = PollSubmissionAnswerSerializer(many=True)

    class Meta:
        model = models.PollSubmission
        fields = ["poll", "answers", "created_at", "updated_at"]

    def create(self, validated_data):
        answers = validated_data.pop("answers", None)
        submission = super().create(validated_data)

        if not answers:
            return submission

        for answer in answers:
            models.PollQuestionAnswer.objects.create(submission=submission, **answer)

        return submission

    def update(self, instance, validated_data):
        raise NotImplementedError("Submission update is not implemented yet.")
        # return super().update(instance, validated_data)
