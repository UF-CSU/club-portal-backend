from django.db import models
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework import exceptions, permissions

from core.abstracts.viewsets import CustomLimitOffsetPagination, ModelViewSetBase
from events.models import EventAttendance
from polls.models import ChoiceInputOption, Poll, PollField, PollSubmission
from polls.serializers import (
    PollChoiceInputOptionSerializer,
    PollFieldSerializer,
    PollSerializer,
    PollSubmissionSerializer,
)
from polls.services import PollService


class PollViewset(ModelViewSetBase):
    """Manage polls in api."""

    queryset = Poll.objects.all()
    serializer_class = PollSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]


class PollSubmissionViewSet(ModelViewSetBase):
    """Submit polls via api."""

    queryset = PollSubmission.objects.all()
    serializer_class = PollSubmissionSerializer
    pagination_class = CustomLimitOffsetPagination
    # permission_classes = []

    def get_queryset(self):
        poll_id = self.kwargs.get("poll_id", None)
        self.queryset = self.queryset.filter(poll__id=poll_id)
        return super().get_queryset()

    def perform_create(self, serializer):
        poll_id = self.kwargs.get("poll_id", None)
        poll = get_object_or_404(Poll, id=poll_id)
        user = self.request.user

        submission = serializer.save(poll=poll, user=user)
        submission = PollService(poll).validate_submission(submission)

        # Mark attendance if poll contains related event
        if poll.event is not None:
            EventAttendance.objects.update_or_create(event=poll.event, user=user)

        return submission

    def perform_update(self, serializer):
        submission = super().perform_update(serializer)
        submission = PollService(submission.poll).validate_submission(submission)

        return submission

    @extend_schema(auth=[{"security": []}, {}])
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)


class PollFieldViewSet(ModelViewSetBase):
    """API for managing poll fields."""

    queryset = PollField.objects.all()
    serializer_class = PollFieldSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        poll_id = self.kwargs.get("poll_id", None)
        self.queryset = self.queryset.filter(poll__id=poll_id)
        return super().get_queryset()

    def perform_create(self, serializer):
        poll_id = self.kwargs.get("poll_id", None)
        poll = get_object_or_404(Poll, id=poll_id)

        serializer.save(poll=poll)


class PollChoiceOptionViewSet(ModelViewSetBase):
    """API for managing poll choice input options."""

    queryset = ChoiceInputOption.objects.all()
    serializer_class = PollChoiceInputOptionSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        poll_id = self.kwargs.get("poll_id", None)
        field_id = self.kwargs.get("field_id", None)

        # get_object_or_404(Poll, id=poll_id)
        self.queryset = self.queryset.filter(
            models.Q(input__question__field__id=field_id)
            & models.Q(input__question__field__poll__id=poll_id)
        )
        return super().get_queryset()

    def perform_create(self, serializer):
        poll_id = self.kwargs.get("poll_id", None)
        field_id = self.kwargs.get("field_id", None)
        poll = get_object_or_404(Poll, id=poll_id)

        field = get_object_or_404(poll.fields, id=field_id)
        if not (
            field.field_type == "question" and field.question.input_type == "choice"
        ):
            raise exceptions.ParseError(detail="Can only add options to a choice input")

        serializer.save(input=field.question.choice_input)
