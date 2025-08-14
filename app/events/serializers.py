from django.core import exceptions
from rest_framework import serializers

from clubs.models import Club
from clubs.serializers import ClubFileNestedSerializer
from core.abstracts.serializers import ModelSerializerBase
from events.models import (
    Event,
    EventAttendance,
    EventAttendanceLink,
    EventCancellation,
    EventHost,
    EventTag,
    RecurringEvent,
)
from events.tasks import sync_recurring_event_task
from lib.celery import delay_task
from polls.models import (
    ChoiceInput,
    ChoiceInputOption,
    PollInputType,
    PollQuestionAnswer,
    PollSubmission,
)
from polls.serializers import PollSerializer, PollSubmissionSerializer
from querycsv.serializers import CsvModelSerializer, WritableSlugRelatedField
from users.models import Profile, User
from users.serializers import ProfileNestedSerializer


class EventTagSerializer(ModelSerializerBase):
    """Group related events."""

    # TODO: This shows as readonly in typegen, shouldn't be readonly
    id = serializers.PrimaryKeyRelatedField(queryset=EventTag.objects.all())

    class Meta:
        model = EventTag
        fields = ["id", "name", "color", "order"]
        read_only_fields = ["name", "color", "order"]


class EventHostSerializer(ModelSerializerBase):
    """JSON representation for hosts inside events."""

    # TODO: Rename to "club" or change to serializers.IntegerField
    club_id = serializers.PrimaryKeyRelatedField(
        source="club", queryset=Club.objects.all()
    )
    club_name = serializers.SlugRelatedField(
        source="club", read_only=True, slug_field="name"
    )
    club_logo = serializers.ImageField(
        source="club.logo", read_only=True, required=False, allow_null=True
    )

    class Meta:
        model = EventHost
        fields = ["id", "club_id", "club_name", "club_logo", "is_primary"]
        read_only_fields = [
            "id",
            "club_name",
            "club_logo",
        ]


class EventAttendanceLinkSerializer(ModelSerializerBase):
    """Represent attendance links for events."""

    qrcode_url = serializers.ImageField(
        source="qrcode.image", read_only=True, help_text="URL for the QRCode SVG"
    )

    class Meta:
        model = EventAttendanceLink
        fields = [
            "id",
            "url",
            "reference",
            "is_tracked",
            "display_name",
            "qrcode_url",
        ]


class EventSerializer(ModelSerializerBase):
    """Represents a calendar event for a single or multiple clubs."""

    status = serializers.CharField(read_only=True)
    duration = serializers.CharField(read_only=True)
    is_all_day = serializers.BooleanField(read_only=True)
    hosts = EventHostSerializer(many=True, required=False)
    tags = EventTagSerializer(many=True, required=False)
    attachments = ClubFileNestedSerializer(many=True, required=False)
    poll = PollSerializer(required=False, allow_null=True)
    attendance_links = EventAttendanceLinkSerializer(many=True, required=False)

    class Meta:
        model = Event
        exclude = ["clubs", "make_public_task"]

    def validate(self, attrs):
        # Ensure that there are not only secondary hosts
        hosts = attrs.get("hosts", None)

        if not self.instance:
            primary_hosts = [
                host for host in hosts if host.get("is_primary", False) is True
            ]

            if len(primary_hosts) == 0 and len(hosts) > 0:
                raise exceptions.ValidationError(
                    "Event with hosts must have a primary host."
                )

        return super().validate(attrs)

    def create(self, validated_data):
        hosts_data = validated_data.pop("hosts", [])
        attachment_data = validated_data.pop("attachments", [])

        event = Event.objects.create(**validated_data)

        for host in hosts_data:

            EventHost.objects.create(
                event=event, club=host["club"], is_primary=host.get("is_primary", False)
            )

        for attachment in attachment_data:
            attachment_id = attachment["id"]

            event.attachments.add(attachment_id)

        return event

    def update(self, instance, validated_data):
        attachment_data = validated_data.pop("attachments", [])

        event = super().update(instance, validated_data)

        event.attachments.clear()

        for attachment in attachment_data:
            attachment_id = attachment["id"]
            event.attachments.add(attachment_id)

        return event


class EventAttendanceUserSerializer(ModelSerializerBase):
    email = serializers.EmailField(required=False)
    profile = ProfileNestedSerializer(required=False)

    class Meta:
        model = User
        fields = ["email", "profile"]


class EventAttendanceSerializer(ModelSerializerBase):
    """Represents event attendance"""

    user = EventAttendanceUserSerializer(required=False)
    poll_submission = PollSubmissionSerializer(required=False, allow_null=True)

    def create(self, validated_data):
        request_user = validated_data.pop("request_user", None)
        user_data = validated_data.pop("user", None)

        # Get user
        if request_user is not None:
            user = request_user
        else:
            if user_data is None:
                raise serializers.ValidationError("User is required if not logged in.")

            email = user_data.pop("email", None)
            if email is None:
                raise serializers.ValidationError("Email is required")

            user = User.objects.find_one(email=email)
            if user is None:
                if user_data.get("profile", None) is None:
                    raise serializers.ValidationError("Profile is missing for new user")

                user = User.objects.create(email=email)

        # Update profile
        if user_data is not None:
            profile_data = user_data.pop("profile", None)

            # Update profile fields on the logged-in user
            if profile_data is not None:
                profile, _ = Profile.objects.get_or_create(user=user)
                for key, value in profile_data.items():
                    setattr(profile, key, value)
                profile.save()

        # Event should always exist in validated_data
        event = validated_data.pop("event")
        poll_submission_data = validated_data.pop("poll_submission", None)

        if event.poll is not None:
            if poll_submission_data is None:
                if event.is_poll_submission_required:
                    raise serializers.ValidationError(
                        "Poll submission is required for this event."
                    )
            else:
                # Create poll submission
                # NOTE: This should probably be moved into a service
                submission = PollSubmission.objects.create(poll=event.poll, user=user)

                answers = poll_submission_data.pop("answers", [])
                for answer in answers:
                    poll_question = answer.pop("question", None)
                    if poll_question is None:
                        raise serializers.ValidationError(
                            "Improper answer, question not specified"
                        )

                    match poll_question.input_type:
                        case PollInputType.TEXT:
                            PollQuestionAnswer.objects.create(
                                question=poll_question,
                                submission=submission,
                                text_value=answer["text_value"],
                            )
                        case PollInputType.RANGE | PollInputType.NUMBER:
                            PollQuestionAnswer.objects.create(
                                question=poll_question,
                                submission=submission,
                                number_value=answer["number_value"],
                            )
                        case PollInputType.CHOICE:
                            choice_input = ChoiceInput.objects.get(
                                question=poll_question
                            )
                            options_data = answer.pop("options_value", [])
                            selected_options = [
                                ChoiceInputOption.objects.get(
                                    input=choice_input, value=selected_option
                                )
                                for selected_option in options_data
                            ]
                            PollQuestionAnswer.objects.create(
                                question=poll_question,
                                submission=submission,
                                options_value=selected_options,
                            )
                        case _:
                            raise serializers.ValidationError(
                                "PollInputType not yet supported"
                            )

                # TODO: Validate submission
                # submission = PollService(event.poll).validate_submission(submission)
                # submission.save()

        event_attendance, _ = EventAttendance.objects.update_or_create(
            event=event, user=user
        )
        return event_attendance

    class Meta:
        model = EventAttendance
        exclude = ["event"]


class EventCancellationSerializer(serializers.ModelSerializer):
    class Meta:
        model = EventCancellation
        fields = "__all__"


class RecurringEventSerializer(ModelSerializerBase):
    """Defines repeating events."""

    attachments = ClubFileNestedSerializer(many=True, required=False)
    is_all_day = serializers.BooleanField(read_only=True)

    class Meta:
        model = RecurringEvent
        fields = "__all__"

    def create(self, validated_data):
        obj = super().create(validated_data)
        delay_task(sync_recurring_event_task, recurring_event_id=obj.id)

        return obj


#############################################################
# MARK: CSV Serializers
#############################################################


class EventCsvSerializer(CsvModelSerializer):
    """CSV Fields for events."""

    clubs = serializers.SlugRelatedField(
        slug_field="name",
        queryset=Club.objects.all(),
        many=True,
        help_text="Club names",
    )
    tags = WritableSlugRelatedField(
        slug_field="name",
        queryset=EventTag.objects.all(),
        many=True,
        help_text="Tag names",
    )

    class Meta:
        model = Event
        fields = "__all__"


class EventAttendanceCsvSerializer(CsvModelSerializer):
    event = None
    name = serializers.CharField(
        write_only=True, max_length=128, help_text="Name of event"
    )
    start_at = serializers.DateTimeField(
        write_only=True, help_text="Start datetime of event"
    )
    end_at = serializers.DateTimeField(
        write_only=True, help_text="End datetime of event"
    )

    user = WritableSlugRelatedField(
        slug_field="email",
        queryset=User.objects.all(),
        help_text="Email of attendee",
    )

    class Meta:
        model = EventAttendance
        exclude = ("event",)

    def validate(self, attrs):
        name = attrs.get("name")
        start_at = attrs.get("start_at")
        end_at = attrs.get("end_at")

        try:
            event = Event.objects.get(
                name=name,
                start_at=start_at,
                end_at=end_at,
            )
        except Event.DoesNotExist:
            raise serializers.ValidationError(
                "Event with the given name, start_at and end_at does not exist."
            )

        attrs["event"] = event
        return attrs

    def create(self, validated_data):
        validated_data.pop("name", None)
        validated_data.pop("start_at", None)
        validated_data.pop("end_at", None)
        return super().create(validated_data)
