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
        exclude = ["question"]


class ChoiceInputOptionNestedSerializer(ModelSerializerBase):
    """Show choice input options in poll question json."""

    value = serializers.CharField(required=False)

    class Meta:
        model = models.ChoiceInputOption
        exclude = ["input"]


class ChoiceInputNestedSerializer(ModelSerializerBase):
    """Show choice input in poll question json."""

    options = ChoiceInputOptionNestedSerializer(many=True)

    class Meta:
        model = models.ChoiceInput
        exclude = ["question"]


class RangeInputNestedSerializer(ModelSerializerBase):
    """Show range input in poll question json."""

    class Meta:
        model = models.RangeInput
        exclude = ["question"]


class UploadInputNestedSerializer(ModelSerializerBase):
    """Show upload input in poll question json."""

    file_types = StringListField(required=False)

    class Meta:
        model = models.UploadInput
        exclude = ["question"]


class NumberInputNestedSerializer(ModelSerializerBase):
    """Show number input in poll question json."""

    class Meta:
        model = models.NumberInput
        exclude = ["question"]


class PollQuestionSerializer(ModelSerializerBase):
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

        # Extract field and pass it as positional argument to PollQuestionManager.create()
        field = validated_data.pop("field")
        label = validated_data.pop("label")
        input_type = validated_data.pop("input_type")

        question = models.PollQuestion.objects.create(
            field=field, label=label, input_type=input_type, **validated_data
        )

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

    def update(self, instance, validated_data):
        """Update question with nested inputs."""

        # Extract input data before updating the question
        text_input = validated_data.pop("text_input", None)
        choice_input = validated_data.pop("choice_input", None)
        range_input = validated_data.pop("range_input", None)
        upload_input = validated_data.pop("upload_input", None)
        number_input = validated_data.pop("number_input", None)

        # Update question fields
        question = super().update(instance, validated_data)

        # Update or create inputs based on input_type
        if question.input_type == "text" and text_input is not None:
            try:
                existing_input = question._text_input
                for attr, value in text_input.items():
                    setattr(existing_input, attr, value)
                existing_input.save()
            except models.TextInput.DoesNotExist:
                models.TextInput.objects.create(**text_input, question=question)

        elif question.input_type == "choice" and choice_input is not None:
            options = choice_input.pop("options", [])
            try:
                existing_input = question._choice_input
                for attr, value in choice_input.items():
                    setattr(existing_input, attr, value)
                existing_input.save()
                choice_input_obj = existing_input
            except models.ChoiceInput.DoesNotExist:
                choice_input_obj = models.ChoiceInput.objects.create(
                    **choice_input, question=question
                )

            # Update options if provided
            if options:
                # Simple approach: delete existing and recreate
                choice_input_obj.options.all().delete()
                for option in options:
                    models.ChoiceInputOption.objects.create(
                        input=choice_input_obj, **option
                    )

        elif question.input_type == "range" and range_input is not None:
            try:
                existing_input = question._range_input
                for attr, value in range_input.items():
                    setattr(existing_input, attr, value)
                existing_input.save()
            except models.RangeInput.DoesNotExist:
                models.RangeInput.objects.create(**range_input, question=question)

        elif question.input_type == "upload" and upload_input is not None:
            try:
                existing_input = question._upload_input
                for attr, value in upload_input.items():
                    setattr(existing_input, attr, value)
                existing_input.save()
            except models.UploadInput.DoesNotExist:
                models.UploadInput.objects.create(**upload_input, question=question)

        elif question.input_type == "number" and number_input is not None:
            try:
                existing_input = question._number_input
                for attr, value in number_input.items():
                    setattr(existing_input, attr, value)
                existing_input.save()
            except models.NumberInput.DoesNotExist:
                models.NumberInput.objects.create(**number_input, question=question)

        return question


class PollMarkupNestedSerializer(ModelSerializerBase):
    """Show markup in poll field json."""

    class Meta:
        model = models.PollMarkup
        fields = ["id", "content", "field"]
        extra_kwargs = {"field": {"required": False}}


class PollFieldSerializer(ModelSerializerBase):
    """Show poll fields  in polls."""

    question = PollQuestionSerializer(required=False)
    markup = PollMarkupNestedSerializer(required=False)

    class Meta:
        model = models.PollField
        fields = ["id", "field_type", "order", "question", "markup"]
        extra_kwargs = {"field_type": {"allow_null": False}}

    def create(self, validated_data):
        question_data = validated_data.pop("question", None)
        markup_data = validated_data.pop("markup", None)

        field = super().create(validated_data)

        if question_data is not None:
            # Pop out inputs
            text_input = question_data.pop("text_input", None)
            choice_input = question_data.pop("choice_input", None)
            range_input = question_data.pop("range_input", None)
            upload_input = question_data.pop("upload_input", None)
            number_input = question_data.pop("number_input", None)

            # Create question
            question = models.PollQuestion.objects.create(**question_data, field=field)

            # Create inputs
            if text_input:
                models.TextInput.objects.create(**text_input, question=question)
            elif choice_input:
                options = choice_input.pop("options", [])
                choice_input = models.ChoiceInput.objects.create(
                    **choice_input, question=question
                )

                for option in options:
                    models.ChoiceInputOption.objects.create(
                        **option, input=choice_input
                    )
            elif range_input:
                models.RangeInput.objects.create(**range_input, question=question)
            elif upload_input:
                models.UploadInput.objects.create(**upload_input, question=question)
            elif number_input:
                models.NumberInput.objects.create(**number_input, question=question)

        elif markup_data is not None:
            models.PollMarkup.objects.create(**markup_data, field=field)

        return field

    def update(self, instance, validated_data):
        """Update field with nested question or markup."""

        question_data = validated_data.pop("question", None)
        markup_data = validated_data.pop("markup", None)

        # Update field instance
        field = super().update(instance, validated_data)

        # Handle question updates
        if question_data is not None:
            try:
                existing_question = field.question
                serializer = PollQuestionSerializer(
                    existing_question, data=question_data, partial=True
                )
                serializer.is_valid(raise_exception=True)
                serializer.save()
            except models.PollQuestion.DoesNotExist:
                serializer = PollQuestionSerializer(
                    data={**question_data, "field": field.id}
                )
                serializer.is_valid(raise_exception=True)
                serializer.save()

        # Handle markup updates
        if markup_data is not None:
            try:
                existing_markup = field.markup
                serializer = PollMarkupNestedSerializer(
                    existing_markup, data=markup_data, partial=True
                )
                serializer.is_valid(raise_exception=True)
                serializer.save()
            except models.PollMarkup.DoesNotExist:
                serializer = PollMarkupNestedSerializer(
                    data={**markup_data, "field": field.id}
                )
                serializer.is_valid(raise_exception=True)
                serializer.save()

        return field


class PollSerializer(ModelSerializer):
    """JSON definition for polls."""

    fields = PollFieldSerializer(many=True, read_only=True)

    class Meta:
        model = models.Poll
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at"]


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
