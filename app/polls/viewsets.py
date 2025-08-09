from django.shortcuts import get_object_or_404
from rest_framework import permissions

from core.abstracts.viewsets import ModelViewSetBase
from events.models import EventAttendance
from polls.models import Poll, PollField, PollSubmission
from polls.serializers import (
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
    permission_classes = []

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
