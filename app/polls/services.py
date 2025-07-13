from core.abstracts.services import ServiceBase
from polls.models import (
    ChoiceInput,
    Poll,
    PollField,
    PollFieldType,
    PollInputType,
    PollMarkup,
    PollQuestion,
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

    def validate_poll_submission(self, submission: PollSubmission):
        """Check if a poll submission is valid."""

        pass
