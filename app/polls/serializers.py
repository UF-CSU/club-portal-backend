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
        fields = ["id", "text_type", "min_length", "max_length"]


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
        fields = ["id", "options"]


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
        ]


class UploadInputNestedSerializer(ModelSerializerBase):
    """Show upload input in poll question json."""

    file_types = StringListField(required=False)

    class Meta:
        model = models.UploadInput
        fields = ["id", "file_types", "max_files"]


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
        ]


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

    def update(self, instance, validated_data):
        """Update field with nested question or markup."""

        question_data = validated_data.pop("question", None)
        markup_data = validated_data.pop("markup", None)

        # Update field instance
        field = super().update(instance, validated_data)

        # Handle question updates
        if question_data is not None:
            try:
                existing_question = field._question
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
                existing_markup = field._markup
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

    fields = PollFieldSerializer(many=True)

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
                serializer = PollQuestionSerializer(
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

    def update(self, instance, validated_data):
        """Update poll with nested fields intelligently."""

        fields_data = validated_data.pop("fields", None)

        # Update poll instance fields (name, description, etc.)
        instance = super().update(instance, validated_data)

        if fields_data is not None:
            self._update_poll_fields(instance, fields_data)

        return instance

    def _update_poll_fields(self, poll_instance, fields_data):
        """Update poll fields with intelligent create/update/delete logic."""

        # Get existing fields
        existing_fields = {field.id: field for field in poll_instance.fields.all()}

        # Track which fields were provided in the update
        updated_field_ids = set()

        for field_data in fields_data:
            field_id = field_data.get("id")
            question_data = field_data.pop("question", None)
            markup_data = field_data.pop("markup", None)

            if field_id and field_id in existing_fields:
                # Update existing field
                field = existing_fields[field_id]
                for attr, value in field_data.items():
                    if attr != "id":
                        setattr(field, attr, value)
                field.save()
                updated_field_ids.add(field_id)
            else:
                # Create new field
                field = models.PollField.objects.create(
                    poll=poll_instance, **field_data
                )
                if field_id:  # If an ID was provided but not found, track it anyway
                    updated_field_ids.add(field.id)

            # Handle question relationship
            if question_data is not None:
                self._update_poll_question(field, question_data)

            # Handle markup relationship
            if markup_data is not None:
                self._update_poll_markup(field, markup_data)

        # Delete fields that weren't included in the update
        fields_to_delete = set(existing_fields.keys()) - updated_field_ids
        if fields_to_delete:
            models.PollField.objects.filter(id__in=fields_to_delete).delete()

    def _update_poll_question(self, field, question_data):
        """Update or create question for a field."""

        try:
            existing_question = field._question
            # Update existing question
            for attr, value in question_data.items():
                if attr not in [
                    "text_input",
                    "choice_input",
                    "range_input",
                    "upload_input",
                    "number_input",
                ]:
                    setattr(existing_question, attr, value)
            existing_question.save()
            question = existing_question
        except models.PollQuestion.DoesNotExist:
            # Create new question
            question = models.PollQuestion.objects.create(
                field=field,
                **{
                    k: v
                    for k, v in question_data.items()
                    if k
                    not in [
                        "text_input",
                        "choice_input",
                        "range_input",
                        "upload_input",
                        "number_input",
                    ]
                },
            )

        # Handle input types
        input_type = question_data.get("input_type", question.input_type)

        if input_type == "text" and "text_input" in question_data:
            self._update_text_input(question, question_data["text_input"])
        elif input_type == "choice" and "choice_input" in question_data:
            self._update_choice_input(question, question_data["choice_input"])
        elif input_type == "range" and "range_input" in question_data:
            self._update_range_input(question, question_data["range_input"])
        elif input_type == "upload" and "upload_input" in question_data:
            self._update_upload_input(question, question_data["upload_input"])
        elif input_type == "number" and "number_input" in question_data:
            self._update_number_input(question, question_data["number_input"])

    def _update_poll_markup(self, field, markup_data):
        """Update or create markup for a field."""

        try:
            existing_markup = field._markup
            # Update existing markup
            for attr, value in markup_data.items():
                if attr != "id":
                    setattr(existing_markup, attr, value)
            existing_markup.save()
        except models.PollMarkup.DoesNotExist:
            # Create new markup
            models.PollMarkup.objects.create(field=field, **markup_data)

    def _update_text_input(self, question, text_input_data):
        """Update or create text input."""

        try:
            existing_input = question._text_input
            for attr, value in text_input_data.items():
                if attr != "id":
                    setattr(existing_input, attr, value)
            existing_input.save()
        except models.TextInput.DoesNotExist:
            models.TextInput.objects.create(question=question, **text_input_data)

    def _update_choice_input(self, question, choice_input_data):
        """Update or create choice input with options."""

        options_data = choice_input_data.pop("options", [])

        try:
            existing_input = question._choice_input
            for attr, value in choice_input_data.items():
                if attr != "id":
                    setattr(existing_input, attr, value)
            existing_input.save()
            choice_input = existing_input
        except models.ChoiceInput.DoesNotExist:
            choice_input = models.ChoiceInput.objects.create(
                question=question, **choice_input_data
            )

        # Update options
        if options_data:
            self._update_choice_options(choice_input, options_data)

    def _update_choice_options(self, choice_input, options_data):
        """Update choice input options."""

        existing_options = {option.id: option for option in choice_input.options.all()}
        updated_option_ids = set()

        for option_data in options_data:
            option_id = option_data.get("id")

            if option_id and option_id in existing_options:
                # Update existing option
                option = existing_options[option_id]
                for attr, value in option_data.items():
                    if attr != "id":
                        setattr(option, attr, value)
                option.save()
                updated_option_ids.add(option_id)
            else:
                # Create new option
                option = models.ChoiceInputOption.objects.create(
                    input=choice_input, **option_data
                )
                if option_id:
                    updated_option_ids.add(option.id)

        # Delete options that weren't included
        options_to_delete = set(existing_options.keys()) - updated_option_ids
        if options_to_delete:
            models.ChoiceInputOption.objects.filter(id__in=options_to_delete).delete()

    def _update_range_input(self, question, range_input_data):
        """Update or create range input."""

        try:
            existing_input = question._range_input
            for attr, value in range_input_data.items():
                if attr != "id":
                    setattr(existing_input, attr, value)
            existing_input.save()
        except models.RangeInput.DoesNotExist:
            models.RangeInput.objects.create(question=question, **range_input_data)

    def _update_upload_input(self, question, upload_input_data):
        """Update or create upload input."""

        try:
            existing_input = question._upload_input
            for attr, value in upload_input_data.items():
                if attr != "id":
                    setattr(existing_input, attr, value)
            existing_input.save()
        except models.UploadInput.DoesNotExist:
            models.UploadInput.objects.create(question=question, **upload_input_data)

    def _update_number_input(self, question, number_input_data):
        """Update or create number input."""

        try:
            existing_input = question._number_input
            for attr, value in number_input_data.items():
                if attr != "id":
                    setattr(existing_input, attr, value)
            existing_input.save()
        except models.NumberInput.DoesNotExist:
            models.NumberInput.objects.create(question=question, **number_input_data)


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
