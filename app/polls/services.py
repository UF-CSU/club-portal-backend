from core.abstracts.schedules import schedule_clocked_func
from core.abstracts.services import ServiceBase
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
    PollTemplate,
    TextInput,
)


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
                    required=q_tpl.required,
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

    def validate_submission(self, submission: PollSubmission, raise_exception=False):
        """Check if a poll submission is valid."""

        for answer in submission.answers.all():
            pass

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


def set_poll_status(poll_id: int, status: PollStatusType):
    """Set a poll as open."""

    poll = Poll.objects.get_by_id(poll_id)
    poll.status = status
    poll.save()
