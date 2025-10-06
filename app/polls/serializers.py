"""
Convert poll models to json objects.
"""

from django.shortcuts import get_object_or_404
from rest_framework import exceptions, serializers

from clubs.models import Club
from core.abstracts.serializers import (
    ModelSerializer,
    ModelSerializerBase,
    UpdateListSerializer,
)
from events.models import Event
from polls import models
from users.models import User
from users.serializers import UserNestedSerializer


class TextInputSerializer(ModelSerializerBase):
    """Text input, textarea, or rich text editor."""

    class Meta:
        model = models.TextInput
        exclude = ["question"]


class ChoiceInputOptionSerializer(ModelSerializerBase):
    """Allow user to select one or multiple options."""

    value = serializers.CharField(required=False)

    class Meta:
        model = models.ChoiceInputOption
        exclude = ["input"]


class ChoiceInputSerializer(ModelSerializerBase):
    """Options given to user for a choice input."""

    options = ChoiceInputOptionSerializer(many=True)

    class Meta:
        model = models.ChoiceInput
        exclude = ["question"]


class ScaleInputSerializer(ModelSerializerBase):
    """Allow user to select number in a linear scale format."""

    class Meta:
        model = models.ScaleInput
        exclude = ["question"]


class UploadInputSerializer(ModelSerializerBase):
    """Allow user to upload file as a ClubFile."""

    class Meta:
        model = models.UploadInput
        exclude = ["question"]


class NumberInputSerializer(ModelSerializerBase):
    """Allow user to enter a plain number."""

    class Meta:
        model = models.NumberInput
        exclude = ["question"]


class EmailInputSerializer(ModelSerializerBase):
    """Text input with extra email validation."""

    class Meta:
        model = models.EmailInput
        exclude = ["question"]


class PhoneInputSerializer(ModelSerializerBase):
    """Text input with extra phone number validation."""

    class Meta:
        model = models.PhoneInput
        exclude = ["question"]


class DateInputSerializer(ModelSerializerBase):
    """Allow user to select a date."""

    class Meta:
        model = models.DateInput
        exclude = ["question"]


class TimeInputSerializer(ModelSerializerBase):
    """Allow user to select a time."""

    class Meta:
        model = models.TimeInput
        exclude = ["question"]


class UrlInputSerializer(ModelSerializerBase):
    """Allow user to enter a valid URL."""

    class Meta:
        model = models.UrlInput
        exclude = ["question"]


class CheckboxInputSerializer(ModelSerializerBase):
    """Allow user to select one or multiple options."""

    class Meta:
        model = models.CheckboxInput
        exclude = ["question"]


class PollQuestionSerializer(ModelSerializerBase):
    """Show questions nested in poll fields."""

    text_input = TextInputSerializer(required=False, allow_null=True)
    choice_input = ChoiceInputSerializer(required=False, allow_null=True)
    scale_input = ScaleInputSerializer(required=False, allow_null=True)
    upload_input = UploadInputSerializer(required=False, allow_null=True)
    number_input = NumberInputSerializer(required=False, allow_null=True)
    email_input = EmailInputSerializer(required=False, allow_null=True)
    phone_input = PhoneInputSerializer(required=False, allow_null=True)
    date_input = DateInputSerializer(required=False, allow_null=True)
    time_input = TimeInputSerializer(required=False, allow_null=True)
    url_input = UrlInputSerializer(required=False, allow_null=True)
    checkbox_input = CheckboxInputSerializer(required=False, allow_null=True)
    answer_field = serializers.ChoiceField(
        read_only=True, choices=models.AnswerFieldType.choices
    )

    class Meta:
        model = models.PollQuestion
        exclude = ["created_at", "updated_at"]
        extra_kwargs = {"field": {"required": False}}

    def get_input_data(self, validated_data: dict):
        """Get dictionary of `{ input_type: input_data }` from validated data."""

        return {
            "text": validated_data.pop("text_input", None),
            "choice": validated_data.pop("choice_input", None),
            "scale": validated_data.pop("scale_input", None),
            "upload": validated_data.pop("upload_input", None),
            "number": validated_data.pop("number_input", None),
            "email": validated_data.pop("email_input", None),
            "phone": validated_data.pop("phone_input", None),
            "date": validated_data.pop("date_input", None),
            "time": validated_data.pop("time_input", None),
            "url": validated_data.pop("url_input", None),
            "checkbox": validated_data.pop("checkbox_input", None),
        }

    def create(self, validated_data):
        """Create question with nested inputs."""

        input_data = self.get_input_data(validated_data)

        # Extract field and pass it as positional argument to PollQuestionManager.create()
        field = validated_data.pop("field")
        label = validated_data.pop("label")
        input_type = validated_data.pop("input_type")

        question = models.PollQuestion.objects.create(
            field=field, label=label, input_type=input_type, **validated_data
        )

        input_kwargs = input_data[input_type] or {}
        question.create_input(**input_kwargs)

        return question

    def update(self, instance, validated_data):
        """Update question with nested inputs."""

        # Extract input data before updating the question
        input_data = self.get_input_data(validated_data)

        # Update question fields
        question = super().update(instance, validated_data)
        input_kwargs = input_data[question.input_type] or {}
        question.update_input(**input_kwargs)

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
        list_serializer_class = (
            UpdateListSerializer  # TODO: Finish implementing bulk updates
        )

    def create(self, validated_data):
        question_data = validated_data.pop("question", None)
        markup_data = validated_data.pop("markup", None)

        field = super().create(validated_data)

        if question_data is not None:
            question_data["field"] = field
            serializer = PollQuestionSerializer()
            serializer.create(question_data)

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
            question_data["field"] = field

            try:
                existing_question = field.question
                serializer = PollQuestionSerializer()
                serializer.update(existing_question, question_data)
            except models.PollQuestion.DoesNotExist:
                serializer = PollQuestionSerializer()
                serializer.create(question_data)

        # Handle markup updates
        if markup_data is not None:
            markup_data["field"] = field.id
            try:
                existing_markup = field.markup
                serializer = PollMarkupNestedSerializer()
                serializer.update(existing_markup, markup_data)
            except models.PollMarkup.DoesNotExist:
                serializer = PollMarkupNestedSerializer()
                serializer.create(markup_data)

        return field


class PollLinkNestedSerializer(ModelSerializerBase):
    """A link a user can use to submit a poll."""

    qrcode_url = serializers.URLField(
        source="qrcode.download_url", read_only=True, help_text="URL for the QRCode SVG"
    )

    class Meta:
        model = models.PollSubmissionLink
        fields = ["id", "url", "qrcode_url", "club"]


class PollNestedSerializer(ModelSerializerBase):
    """Show minimum information for a poll"""

    class Meta:
        model = models.Poll
        exclude = []


class PollEventNestedSerializer(ModelSerializerBase):
    """Show event for a poll."""

    id = serializers.IntegerField()
    attendance_links = PollLinkNestedSerializer(many=True)

    class Meta:
        model = Event
        fields = ["id", "name", "start_at", "end_at", "attendance_links"]
        read_only_fields = ["name", "start_at", "end_at", "attendance_links"]


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
    link = PollLinkNestedSerializer(
        read_only=True, allow_null=True, source="submission_link"
    )

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


class PollPreviewSerializer(ModelSerializer):
    """Fields guest users can see for polls."""

    fields = PollFieldSerializer(many=True, read_only=True)
    status = serializers.ChoiceField(
        choices=models.PollStatusType.choices, read_only=True
    )
    is_published = serializers.BooleanField(required=False)
    poll_type = serializers.ChoiceField(choices=models.PollType.choices, read_only=True)
    event = PollEventNestedSerializer(required=False, allow_null=True)
    club = PollClubNestedSerializer(required=True, allow_null=True)
    link = PollLinkNestedSerializer(
        read_only=True, allow_null=True, source="submission_link"
    )

    class Meta:
        model = models.Poll
        exclude = ["open_task", "close_task"]
        read_only_fields = ["id", "created_at", "updated_at"]


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
        self.fields[
            "options_value"
        ].child_relation.queryset = models.ChoiceInputOption.objects.filter(
            input__question__id=question_id
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
        answers: list = validated_data.pop("answers", [])
        user = validated_data.get("user", None)

        email_answer = None
        for answer in answers:
            if answer.get("question").is_user_lookup:
                email_answer = answer.get("text_value", None)
                break

        if not user or user.is_anonymous:
            if not email_answer:
                raise exceptions.ValidationError(
                    {"answers": "Missing user lookup field"}, code="required"
                )
            try:
                user = User.objects.get_by_email(email_answer)
            except User.DoesNotExist:
                user = User.objects.create(email=email_answer)
        # elif not email_answer:
        #     # TODO: Set ufl email if email field has it enabled
        #     answers.append({"email": user.email})

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
