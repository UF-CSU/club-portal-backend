from django.db import models, transaction
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework import exceptions, mixins, permissions


from core.abstracts.viewsets import ModelViewSetBase, ViewSetBase
from polls.models import (
    ChoiceInputOption,
    Poll,
    PollField,
    PollStatusType,
    PollSubmission,
)
from polls.serializers import (
    ChoiceInputOptionSerializer,
    PollFieldSerializer,
    PollPreviewSerializer,
    PollSerializer,
    PollSubmissionSerializer,
)
from polls.services import PollService


class PollPreviewViewSet(mixins.RetrieveModelMixin, ViewSetBase):
    """Show polls for guest viewers."""

    serializer_class = PollPreviewSerializer
    queryset = Poll.objects.all()
    permission_classes = [permissions.AllowAny]


class PollViewset(ModelViewSetBase):
    """Manage polls in api."""

    queryset = Poll.objects.all()
    serializer_class = PollSerializer

    def get_queryset(self):
        user_clubs = self.request.user.clubs.all().values_list("id", flat=True)
        self.queryset = self.queryset.filter(club__id__in=user_clubs)
        return super().get_queryset()


class PollFieldViewSet(ModelViewSetBase):
    """API for managing poll fields."""

    queryset = PollField.objects.all()
    serializer_class = PollFieldSerializer

    def check_object_permissions(self, request, obj):
        # FIXME: This patches issue with updating fields, but this should be done by perms backend
        if request.user.is_club_admin:
            return True
        return super().check_object_permissions(request, obj)

    def get_queryset(self):
        poll_id = self.kwargs.get("poll_id", None)
        self.queryset = self.queryset.filter(poll__id=poll_id)
        return super().get_queryset()

    def perform_create(self, serializer):
        poll_id = self.kwargs.get("poll_id", None)
        poll = get_object_or_404(Poll, id=poll_id)

        with transaction.atomic():
            serializer.save(poll=poll)


class PollChoiceOptionViewSet(ModelViewSetBase):
    """API for managing poll choice input options."""

    queryset = ChoiceInputOption.objects.all()
    serializer_class = ChoiceInputOptionSerializer

    def get_queryset(self):
        poll_id = self.kwargs.get("poll_id", None)
        field_id = self.kwargs.get("field_id", None)

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


class PollSubmissionViewSet(ModelViewSetBase):
    """Submit polls via api."""

    queryset = PollSubmission.objects.all()
    serializer_class = PollSubmissionSerializer

    def check_permissions(self, request):
        if self.action == "create":
            return True
        return super().check_permissions(request)

    def get_queryset(self):
        poll_id = self.kwargs.get("poll_id", None)
        self.queryset = self.queryset.filter(poll__id=poll_id)
        return super().get_queryset()

    def perform_create(self, serializer):
        poll_id = self.kwargs.get("poll_id", None)
        poll = get_object_or_404(Poll, id=poll_id)

        if poll.status != PollStatusType.OPEN:
            raise exceptions.ParseError(
                detail="Cannot create submission for poll that is not open"
            )

        service = PollService(poll)
        user = self.request.user

        submission = serializer.save(poll=poll, user=user)
        submission = service.process_submission(submission)

        return submission

    def perform_update(self, serializer):
        submission = super().perform_update(serializer)
        submission = PollService(submission.poll).process_submission(submission)

        return submission

    @extend_schema(auth=[{"security": []}, {}])
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)
