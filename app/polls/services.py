import pandas as pd
import pytz
from django.utils import timezone

from app.settings import POLL_SUBMISSION_REDIRECT_URL
from core.abstracts.schedules import schedule_clocked_func
from core.abstracts.services import ServiceBase
from events.models import EventAttendance
from polls.models import (
    ChoiceInput,
    Poll,
    PollField,
    PollFieldType,
    PollInputType,
    PollMarkup,
    PollQuestion,
    PollStatusType,
    PollSubmission,
    PollSubmissionLink,
    PollTemplate,
    PollUserFieldType,
    TextInput,
)
from utils.logging import print_error


class PollTemplateService(ServiceBase[PollTemplate]):
    """Business logic for polls."""

    model = PollTemplate

    def _clone_input(self, question_tpl: PollQuestion, target_question: PollQuestion):
        """Clone question to poll."""

        match question_tpl.input_type:
            case PollInputType.TEXT:
                TextInput.objects.create(
                    question=target_question,
                    text_type=question_tpl.text_input.text_type,
                    min_length=question_tpl.text_input.min_length,
                    max_length=question_tpl.text_input.max_length,
                )
            case PollInputType.CHOICE:
                ChoiceInput.objects.create(
                    questin=target_question,
                )

    def _clone_field(self, field_tpl: PollField, target_poll: Poll):
        """Clone field to poll."""

        field = target_poll.add_field(field_type=field_tpl.field_type)

        match field.field_type:
            case PollFieldType.QUESTION:
                q_tpl = field_tpl.question
                question = PollQuestion.objects.create(
                    field=field,
                    label=q_tpl.label,
                    input_type=q_tpl.input_type,
                    create_input=False,
                    description=q_tpl.description,
                    required=q_tpl.is_required,
                )
                self._clone_input(q_tpl, question)
            case PollFieldType.MARKUP:
                PollMarkup.objects.create(field=field, content=field_tpl.markup.content)

        return field

    def create_poll(self) -> Poll:
        """Create a new poll from this one if it is a template."""

        poll = Poll.objects.create(name=self.obj.name, description=self.obj.description)

        for field_tpl in self.obj.fields.all():
            self._clone_field(field_tpl, poll)


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
        field = kwargs.pop(
            "field",
            PollField.objects.create(poll, field_type="question"),
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
