import pandas as pd
import pytz
from app.settings import POLL_SUBMISSION_REDIRECT_URL
from core.abstracts.schedules import schedule_clocked_func
from core.abstracts.services import ServiceBase
from django.db import connection, models, transaction
from django.template.loader import render_to_string
from django.utils import timezone
from events.models import EventAttendance
from utils.db import dictfetchall
from utils.logging import print_error

from polls.models import (
    Poll,
    PollField,
    PollInputType,
    PollQuestion,
    PollQuestionAnswer,
    PollStatusType,
    PollSubmission,
    PollSubmissionLink,
    PollTemplate,
    PollUserFieldType,
)
from polls.serializers import (
    PollAnalyticsSubmissionsHeatmapSerializer,
    PollSubmissionSerializer,
)


class PollService(ServiceBase[Poll]):
    """Business logic for polls."""

    model = Poll

    def _validate_submission(self, submission: PollSubmission, raise_exception=False):
        """Check if a poll submission is valid."""

        for _answer in submission.answers.all():
            pass

        return submission

    def _remove_task(self, field):
        task = getattr(self.obj, field)
        setattr(self.obj, field, None)
        task.delete()

    def _schedule_poll_open(self):
        """Maked a periodic task for opening the poll."""

        if self.obj.open_task is not None:
            self._remove_task("open_task")

        task = schedule_clocked_func(
            name=f"Set {self.obj.name} as open",
            due_at=self.obj.open_at,
            func=set_poll_status,
            kwargs={"poll_id": self.obj.id, "status": PollStatusType.OPEN},
        )
        self.obj.open_task = task

    def _schedule_poll_close(self):
        """Maked a periodic task for closing the poll."""

        if self.obj.close_task is not None:
            self._remove_task("close_task")

        task = schedule_clocked_func(
            name=f"Set {self.obj.name} as closed",
            due_at=self.obj.close_at,
            func=set_poll_status,
            kwargs={"poll_id": self.obj.id, "status": PollStatusType.CLOSED},
        )
        self.obj.close_task = task

    def sync_status_tasks(self):
        """
        Ensure the poll has periodic tasks if `open_at` and/or `close_at` are set.
        """

        poll = self.obj
        poll.refresh_from_db()

        has_open_at = poll.open_at is not None
        has_open_task = poll.open_task is not None
        has_close_at = poll.close_at is not None
        has_close_task = poll.close_task is not None

        # Sync open task
        if not has_open_at and has_open_task:
            self._remove_task("open_task")
        elif has_open_at and not has_open_task:
            self._schedule_poll_open()
        elif (
            has_open_at
            and has_open_task
            and poll.open_at != poll.open_task.clocked.clocked_time
        ):
            self._schedule_poll_open()

        # Sync close task
        if not has_close_at and has_close_task:
            self._remove_task("close_task")
        elif has_close_at and not has_close_task:
            self._schedule_poll_close()
        elif (
            has_close_at
            and has_close_task
            and poll.close_at != poll.close_task.clocked.clocked_time
        ):
            self._schedule_poll_close()

        poll.save()

    @staticmethod
    def get_submissions(poll_id: int):
        """Get all submissions for a poll."""
        submissions = (
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
        serializer = PollSubmissionSerializer(submissions, many=True)
        return serializer.data

    def get_submissions_df(self, tzname=None) -> pd.DataFrame:
        """Convert submissions to pandas dataframe."""

        data = []
        tzname = tzname or "UTC"

        for submission in self.obj.submissions.all():
            try:
                row = {
                    "User ID": submission.user.id,
                    # "User Email": submission.user.email,
                    "User School Email": submission.user.profile.school_email,
                    "Submission Date": timezone.localtime(
                        submission.created_at, timezone=pytz.timezone(tzname)
                    ),
                    **{
                        answer.label: answer.value
                        for answer in submission.answers.all()
                    },
                }
            except Exception as e:
                row = {"User ID": submission.user.id}
                print_error()
                print(e)

            data.append(row)

        return pd.DataFrame(data)

    def create_question(self, label: str, input_type=PollInputType.TEXT, **kwargs):
        """Create new question, with associated field and input for poll."""

        poll = self.obj
        field = kwargs.pop("field", None) or PollField.objects.create(
            poll=poll, field_type="question"
        )
        payload = {
            "field": field,
            "label": label,
            "input_type": input_type,
            "create_input": True,
            **kwargs,
        }
        return PollQuestion.objects.create(**payload)

    def _update_user_fields_from_submission(self, submission: PollSubmission):
        """For each answer with a linked user field in submission, update user field."""

        answers = submission.answers.all()
        user = submission.user

        if not user:
            return

        for answer in answers:
            if answer.question.link_user_field is None:
                continue

            match answer.question.link_user_field:
                case PollUserFieldType.NAME:
                    user.profile.name = answer.value or user.profile.name
                    user.profile.save()
                case PollUserFieldType.PHONE:
                    user.profile.phone = answer.value or user.profile.phone
                    user.profile.save()
                case PollUserFieldType.MAJOR:
                    user.profile.major = answer.value or user.profile.major
                    user.profile.save()
                case PollUserFieldType.MINOR:
                    user.profile.minor = answer.value or user.profile.minor
                    user.profile.save()
                case PollUserFieldType.COLLEGE:
                    user.profile.college = answer.value or user.profile.college
                    user.profile.save()
                case PollUserFieldType.GRADUATION_YEAR:
                    user.profile.graduation_year = (
                        answer.value or user.profile.graduation_year
                    )
                    user.profile.save()

    def process_submission(self, submission: PollSubmission):
        """Run all actions for submission object."""

        assert submission.poll.pk == self.obj.pk, (
            f"Invalid submission, expected poll id {self.obj.pk} but found {submission.poll.id}."
        )

        self._validate_submission(submission)
        self._update_user_fields_from_submission(submission)

        if self.obj.event is not None:
            EventAttendance.objects.get_or_create(
                user=submission.user, event=self.obj.event
            )

        submission.refresh_from_db()
        return submission

    def create_submission_link(self):
        """Create link where users can fill out poll."""

        with transaction.atomic():
            if self.obj.submission_link is not None:
                return

            url = POLL_SUBMISSION_REDIRECT_URL % {"id": self.obj.id}
            return PollSubmissionLink.objects.create(
                target_url=url, poll=self.obj, club=self.obj.club, create_qrcode=True
            )

    def sync_submission_link(self):
        """Remove and recreate submission links."""

        if self.obj.submission_link is not None:
            PollSubmissionLink.objects.filter(id=self.obj.submission_link.id).delete()

        self.create_submission_link()


def set_poll_status(poll_id: int, status: PollStatusType):
    """Set a poll as open."""

    poll = Poll.objects.get_by_id(poll_id)
    poll.status = status
    poll.save()


class PollTemplateService(ServiceBase[PollTemplate]):
    """Business logic for poll templates."""

    model = PollTemplate

    def _clone_field(
        self,
        template_field: PollField,
        target_poll: Poll,
        target_poll_service: PollService,
    ):
        """Clone field to poll."""

        cloned_field = PollField.objects.create(
            poll=target_poll,
            order=template_field.order,
            field_type=template_field.field_type,
        )

        # Clone question
        question = template_field.question
        if question is not None:
            target_poll_service.create_question(
                question.label,
                question.input_type,
                field=cloned_field,
                description=question.description,
                image=question.image,
                is_required=question.is_required,
                is_user_lookup=question.is_user_lookup,
                link_user_field=question.link_user_field,
            )

    def create_poll(self, **kwargs) -> Poll:
        """Create a new poll from this one if it is a template."""

        # Create the poll
        data = {
            "name": self.obj.name,
            "description": self.obj.description,
            "club": self.obj.club,
            "is_private": self.obj.is_private,
            **kwargs,
        }
        poll = Poll.objects.create(**data, template=self.obj)

        # Set allowed club roles
        poll.allowed_club_roles.set(self.obj.allowed_club_roles.all())

        poll_service = PollService(poll)

        # Clone each field
        template_fields = self.obj.fields.all().order_by("order")
        for template_field in template_fields:
            self._clone_field(template_field, poll, poll_service)

        # Refresh to get accurate field count
        poll.refresh_from_db()
        return poll


class PollAnalyticsService(ServiceBase[Poll]):
    """Business logic for poll analytics"""

    model = Poll

    def get_total_submissions(self) -> int:
        return self.obj.submissions_count

    def get_open_duration_seconds(self) -> int:
        return (timezone.now() - self.obj.open_at).total_seconds()

    def get_total_users(self) -> int:
        return (
            PollSubmission.objects.filter(poll__pk=self.obj.pk)
            .values("user")
            .distinct()
            .count()
        )

    def get_total_guest_users(self) -> int:
        query = render_to_string("get-total-guest-users.sql", {"poll_id": self.obj.pk})
        with connection.cursor() as cursor:
            cursor.execute(query)
            result = dictfetchall(cursor)

            return result[0]["total_guest_users"]

    def get_total_recurring_users(self) -> int:
        query = render_to_string(
            "get-total-recurring-users.sql", {"club_id": self.obj.club.pk}
        )
        with connection.cursor() as cursor:
            cursor.execute(query)
            result = dictfetchall(cursor)

            return result[0]["total_recurring_users"]

    def get_total_submissions_change_from_average(self) -> float:
        query = render_to_string(
            "get-total-submissions-change-from-average.sql",
            {"poll_id": self.obj.pk, "club_id": self.obj.club.pk},
        )
        with connection.cursor() as cursor:
            cursor.execute(query)
            result = dictfetchall(cursor)

            return result[0]["total_submissions_change_from_average"]

    def get_submissions_heatmap(
        self, minutes: int, hours: int
    ) -> PollAnalyticsSubmissionsHeatmapSerializer:
        bin_interval = f"{minutes} minutes"
        interval_limit = f"{hours} hours"
        query = render_to_string(
            "get-submissions-heatmap.sql",
            {
                "poll_id": self.obj.pk,
                "bin_interval": bin_interval,
                "interval_limit": interval_limit,
            },
        )
        with connection.cursor() as cursor:
            cursor.execute(query)
            result = {
                "interval_minutes": minutes,
                "intervals": dictfetchall(cursor)[0]["submissions_heatmap"],
            }

            return result

    def get_questions(self):
        query = render_to_string("get-questions.sql", {"poll_id": self.obj.pk})
        with connection.cursor() as cursor:
            cursor.execute(query)
            result = dictfetchall(cursor)

            return result
