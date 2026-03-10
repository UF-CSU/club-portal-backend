from clubs.viewsets import ClubQueryFilter
from core.abstracts.viewsets import ModelViewSetBase, ViewSetBase
from django.db import models, transaction
from django.forms import model_to_dict
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework import exceptions, mixins, permissions
from rest_framework.generics import RetrieveAPIView
from rest_framework.request import Request
from rest_framework.response import Response

from polls.models import (
    ChoiceInputOption,
    Poll,
    PollField,
    PollQuestionAnswer,
    PollStatusType,
    PollSubmission,
    PollTemplate,
)
from polls.permissions import (
    CanSubmitPoll,
    CanViewPoll,
)
from polls.serializers import (
    ChoiceInputOptionSerializer,
    PollAnalyticsSerializer,
    PollFieldSerializer,
    PollPreviewSerializer,
    PollSerializer,
    PollSubmissionSerializer,
    PollTemplateSerializer,
)
from polls.services import PollAnalyticsService, PollService


class PollPreviewViewSet(mixins.RetrieveModelMixin, ViewSetBase):
    """Show polls for guest viewers."""

    serializer_class = PollPreviewSerializer

    queryset = Poll.objects.select_related("club", "event").prefetch_related(
        models.Prefetch(
            "fields",
            queryset=PollField.objects.select_related(
                "_question",
                "_markup",
                "_question___textinput",
                "_question___choiceinput",
                "_question___scaleinput",
                "_question___uploadinput",
                "_question___numberinput",
                "_question___emailinput",
                "_question___phoneinput",
                "_question___dateinput",
                "_question___timeinput",
                "_question___urlinput",
                "_question___checkboxinput",
            ),
        ),
        "_submission_link__qrcode",
    )

    permission_classes = [CanViewPoll]

    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    # TODO: Refactor to use get_object
    # def retrieve(self, request: Request, *args, **kwargs):
    #     poll_id = self.kwargs.get("pk")
    #     cached_preview = check_cache(DETAIL_POLL_PREVIEW_PREFIX, poll_id=poll_id)

    #     if not cached_preview:
    #         cached_preview = PollPreviewSerializer(Poll.objects.get_by_id(poll_id)).data
    #         set_cache(cached_preview, DETAIL_POLL_PREVIEW_PREFIX, poll_id=poll_id)

    #     return Response(cached_preview)


class PollViewset(ModelViewSetBase):
    """Manage polls in api."""

    serializer_class = PollSerializer
    queryset = Poll.objects.none()
    filter_backends = [ClubQueryFilter]

    def get_queryset(self):
        user_clubs = self.request.user.clubs.all().values_list("id", flat=True)

        return (
            Poll.objects.filter(club__id__in=user_clubs)
            .select_related("club", "event")
            .prefetch_related(
                models.Prefetch(
                    "fields",
                    queryset=PollField.objects.select_related(
                        "_markup",
                        "_question",
                        "_question___textinput",
                        "_question___choiceinput",
                        "_question___scaleinput",
                        "_question___uploadinput",
                        "_question___numberinput",
                        "_question___emailinput",
                        "_question___phoneinput",
                        "_question___dateinput",
                        "_question___timeinput",
                        "_question___urlinput",
                        "_question___checkboxinput",
                    ).order_by("order", "id"),
                ),
                "_submission_link__qrcode",
                "submissions",
            )
            .annotate(
                submissions_count=models.Count("submissions", distinct=True),
                last_submission_at=models.Max("submissions__created_at"),
            )
        )


class PollAnalyticsView(RetrieveAPIView):
    """View various poll analytics for a specific poll"""

    serializer_class = PollAnalyticsSerializer
    queryset = Poll.objects.all()
    permission_classes = [permissions.IsAuthenticated]

    def retrieve(self, request: Request, *args, **kwargs):
        poll_id = self.kwargs.get("poll_id")
        poll = get_object_or_404(Poll, id=poll_id)
        if not request.user.has_perm("polls.view_poll_analytics", poll):
            return HttpResponseForbidden(
                'User does not have "polls.view_poll_analytics" permissions'
            )

        service = PollAnalyticsService(poll)

        analyticsData = {
            "total_submissions": service.get_total_submissions(),
            "open_duration_seconds": service.get_open_duration_seconds(),
            "total_users": service.get_total_users(),
            "total_guest_users": service.get_total_guest_users(),
            "total_recurring_users": service.get_total_recurring_users(),
            "submissions_heatmap": service.get_submissions_heatmap(5, 3),
            "total_submissions_change_from_average": service.get_total_submissions_change_from_average(),
            "questions": service.get_questions(),
        }

        pollData = model_to_dict(poll)
        serializer = self.get_serializer(analyticsData | pollData)

        return Response(serializer.data)


class PollTemplateViewSet(ModelViewSetBase):
    """Manage poll templates in api"""

    queryset = PollTemplate.objects.all()
    serializer_class = PollTemplateSerializer

    def get_queryset(self):
        user_clubs = self.request.user.clubs.all().values_list("id", flat=True)

        return (
            PollTemplate.objects.filter(club__id__in=user_clubs)
            .select_related("club", "event")
            .prefetch_related(
                models.Prefetch(
                    "fields",
                    queryset=PollField.objects.select_related(
                        "_markup",
                        "_question",
                        "_question___textinput",
                        "_question___choiceinput",
                        "_question___scaleinput",
                        "_question___uploadinput",
                        "_question___numberinput",
                        "_question___emailinput",
                        "_question___phoneinput",
                        "_question___dateinput",
                        "_question___timeinput",
                        "_question___urlinput",
                        "_question___checkboxinput",
                    ).order_by("order", "id"),
                ),
                "_submission_link__qrcode",
                "submissions",
            )
            .annotate(
                submissions_count=models.Count("submissions", distinct=True),
                last_submission_at=models.Max("submissions__created_at"),
            )
        )


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

    serializer_class = PollSubmissionSerializer

    def initial(self, request, *args, **kwargs):
        poll_id = self.kwargs.get("poll_id", None)
        self.poll = get_object_or_404(Poll, id=poll_id)

        super().initial(request, *args, **kwargs)

    def check_permissions(self, request):
        if self.action == "create":
            # If submitting poll, override permissions to use the separate permissions
            # flow for submitting polls, which is determined by the poll object
            return CanSubmitPoll().has_object_permission(request, self, self.poll)

        # Default to normal CRUD permissions for PollSubmission objects
        return super().check_permissions(request)

    def get_queryset(self):
        poll_id = self.kwargs.get("poll_id")
        return (
            PollSubmission.objects.filter(poll_id=poll_id)
            .select_related("user", "user__profile")
            .prefetch_related(
                models.Prefetch(
                    "answers",
                    queryset=PollQuestionAnswer.objects.prefetch_related(
                        "options_value"
                    ),
                ),
                "user__verified_emails",
            )
        )

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
