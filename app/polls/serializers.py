"""
Convert poll models to json objects.
"""

from django.shortcuts import get_object_or_404
from rest_framework import exceptions, serializers

from clubs.models import Club
from core.abstracts.serializers import ModelSerializer, ModelSerializerBase
from events.models import Event
from polls import models
from users.models import User
from users.serializers import UserNestedSerializer


class PollTextInputSerializer(ModelSerializerBase):
    """Show text input in poll question json."""

    class Meta:
        model = models.TextInput
        exclude = ["question"]


class PollChoiceInputOptionSerializer(ModelSerializerBase):
    """Show choice input options in poll question json."""

    value = serializers.CharField(required=False)

    class Meta:
        model = models.ChoiceInputOption
        exclude = ["input"]


class PollChoiceInputSerializer(ModelSerializerBase):
    """Show choice input in poll question json."""

    options = PollChoiceInputOptionSerializer(many=True)

    class Meta:
        model = models.ChoiceInput
        exclude = ["question"]


class PollRangeInputSerializer(ModelSerializerBase):
    """Show range input in poll question json."""

    class Meta:
        model = models.RangeInput
        exclude = ["question"]


class PollUploadInputSerializer(ModelSerializerBase):
    """Show upload input in poll question json."""

    # file_types = StringListField(required=False)

    class Meta:
        model = models.UploadInput
        exclude = ["question"]


class PollNumberInputSerializer(ModelSerializerBase):
    """Show number input in poll question json."""

    class Meta:
        model = models.NumberInput
        exclude = ["question"]


class PollQuestionSerializer(ModelSerializerBase):
    """Show questions nested in poll fields."""

    text_input = PollTextInputSerializer(required=False, allow_null=True)
    choice_input = PollChoiceInputSerializer(required=False, allow_null=True)
    range_input = PollRangeInputSerializer(required=False, allow_null=True)
    upload_input = PollUploadInputSerializer(required=False, allow_null=True)
    number_input = PollNumberInputSerializer(required=False, allow_null=True)

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
                existing_input = question.text_input
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
        fields = ["id", "content", "field", "label"]
        extra_kwargs = {"field": {"required": False}}


class PollFieldSerializer(ModelSerializerBase):
    """Show poll fields  in polls."""

    question = PollQuestionSerializer(required=False, allow_null=True)
    markup = PollMarkupNestedSerializer(required=False, allow_null=True)
    order = serializers.IntegerField(required=False)

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


class PollEventNestedSerializer(ModelSerializerBase):
    """Show event for a poll."""

    id = serializers.IntegerField()

    class Meta:
        model = Event
        fields = ["id", "name", "start_at", "end_at"]
        read_only_fields = ["name", "start_at", "end_at"]


class PollClubNestedSerializer(ModelSerializerBase):
    """Display club fields for a poll."""

    id = serializers.IntegerField()

    class Meta:
        model = Club
        fields = ["id", "name"]
        read_only_fields = ["name"]


class PollSerializer(ModelSerializer):
    """JSON definition for polls."""

    fields = PollFieldSerializer(many=True, read_only=True)
    submissions_count = serializers.IntegerField(read_only=True)
    last_submission_at = serializers.DateTimeField(read_only=True, allow_null=True)
    is_published = serializers.BooleanField(required=False)
    status = serializers.ChoiceField(
        choices=models.PollStatusType.choices, read_only=True
    )
    poll_type = serializers.ChoiceField(choices=models.PollType.choices, read_only=True)
    event = PollEventNestedSerializer(required=False, allow_null=True)
    submissions_download_url = serializers.URLField(read_only=True)
    club = PollClubNestedSerializer(required=True, allow_null=True)

    class Meta:
        model = models.Poll
        exclude = ["open_task", "close_task"]
        read_only_fields = ["id", "created_at", "updated_at"]

    def create(self, validated_data):
        club = validated_data.pop("club")
        event = validated_data.pop("event", None)

        validated_data["club"] = get_object_or_404(Club, id=club.get("id"))
        if event:
            validated_data["event"] = get_object_or_404(Event, id=event.get("id"))

        return super().create(validated_data)


class PollSubmissionAnswerSerializer(ModelSerializerBase):
    """Record a user's answer for a specific question."""

    options_value = serializers.SlugRelatedField(
        many=True,
        required=False,
        slug_field="value",
        queryset=models.ChoiceInputOption.objects.all(),
    )
    is_valid = serializers.BooleanField(read_only=True)

    class Meta:
        model = models.PollQuestionAnswer
        exclude = ["submission"]

    def run_prevalidation(self, data=None):
        data.pop("options_value", [])
        question_id = data.get("question")

        res = super().run_prevalidation(data)
        self.fields["options_value"].child_relation.queryset = (
            models.ChoiceInputOption.objects.filter(input__question__id=question_id)
        )

        return res


class PollSubmissionSerializer(ModelSerializerBase):
    """A user's submission for a form."""

    # Poll id is set in the url
    poll = serializers.PrimaryKeyRelatedField(read_only=True)
    answers = PollSubmissionAnswerSerializer(many=True, required=False)
    user = UserNestedSerializer(read_only=True)

    class Meta:
        model = models.PollSubmission
        fields = [
            "id",
            "poll",
            "is_valid",
            "user",
            "answers",
            "created_at",
            "updated_at",
        ]

    def create(self, validated_data):
        answers = validated_data.pop("answers", None)
        user = validated_data.get("user", None)

        if not user or user.is_anonymous:
            email_answer = None
            for answer in answers:
                if answer.get("question").is_user_lookup:
                    email_answer = answer.get("text_value", None)
                    break

            if not email_answer:
                raise exceptions.ValidationError(
                    {"answers": "Missing user lookup field"}, code="required"
                )

            try:
                user = User.objects.get_by_email(email_answer)
            except User.DoesNotExist:
                user = User.objects.create(email=email_answer)

        validated_data["user"] = user
        submission, _ = models.PollSubmission.objects.get_or_create(
            user=user, poll=validated_data["poll"]
        )

        if not answers:
            return submission

        for answer in answers:
            question = answer.pop("question")
            models.PollQuestionAnswer.objects.update_or_create(
                submission=submission, question=question, defaults=answer
            )

        return submission

    def update(self, instance, validated_data):
        raise NotImplementedError("Submission update is not implemented yet.")
        # return super().update(instance, validated_data)
