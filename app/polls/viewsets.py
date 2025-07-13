from django.shortcuts import get_object_or_404

from core.abstracts.viewsets import ModelViewSetBase
from polls.models import Poll, PollSubmission
from polls.serializers import PollSerializer, PollSubmissionSerializer
from polls.services import PollService


class PollViewset(ModelViewSetBase):
    """Manage polls in api."""

    queryset = Poll.objects.all()
    serializer_class = PollSerializer


class PollSubmissionViewSet(ModelViewSetBase):
    """Submit polls via api."""

    queryset = PollSubmission.objects.all()
    serializer_class = PollSubmissionSerializer

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

        return submission

    def perform_update(self, serializer):
        submission = super().perform_update(serializer)
        submission = PollService(submission.poll).validate_submission(submission)

        return submission
