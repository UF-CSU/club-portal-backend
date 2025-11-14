import random

from clubs.tests.utils import create_test_club
from django.urls import reverse
from lib.faker import fake
from users.tests.utils import create_test_user

from polls.models import (
    Poll,
    PollField,
    PollFieldType,
    PollInputType,
    PollQuestion,
    PollQuestionAnswer,
    PollSubmission,
)

POLLS_URL = reverse("api-polls:poll-list")
POLL_PREVIEW_LIST_URL = reverse("api-polls:pollpreview-list")


def polls_detail_url(id: int):
    return reverse("api-polls:poll-detail", args=[id])


def pollpreview_detail_url(id: int):
    return reverse("api-polls:pollpreview-detail", args=[id])


def pollsubmission_list_url(poll_id: int):
    return reverse("api-polls:pollsubmission-list", kwargs={"poll_id": poll_id})


def pollfield_list_url(poll_id: int):
    return reverse("api-polls:pollfield-list", args=[poll_id])


def pollfield_detail_url(poll_id: int, pollfield_id: int):
    return reverse("api-polls:pollfield-detail", args=[poll_id, pollfield_id])


def polloption_list_url(poll_id: int, pollfield_id: int):
    return reverse("api-polls:pollchoiceoption-list", args=[poll_id, pollfield_id])


def polloption_detail_url(poll_id: int, pollfield_id: int, id: int):
    return reverse("api-polls:pollchoiceoption-detail", args=[poll_id, pollfield_id, id])


def create_test_poll(**kwargs):
    """Create mock poll for testing."""

    club = kwargs.pop("club", create_test_club())

    payload = {
        "name": fake.title(),
        "description": fake.paragraph(),
        **kwargs,
    }

    return Poll.objects.create(club=club, **payload)


def create_test_pollquestion(poll: Poll, input_type=PollInputType.TEXT, **kwargs):
    """Create mock poll field for testing."""

    field = kwargs.pop("field", PollField.objects.create(poll, field_type="question"))

    payload = {"label": fake.title(2), **kwargs}
    return PollQuestion.objects.create(
        field=field, input_type=input_type, create_input=True, **payload
    )


def create_test_pollsubmission(poll: Poll, user=None, **kwargs):
    """Create mock poll submission for testing."""

    user = user or create_test_user()

    submission = PollSubmission.objects.create(poll=poll, user=user)

    for field in poll.fields.all():
        if not field.field_type == PollFieldType.QUESTION:
            continue

        q = field.question
        answer_payload = {"question": q, "submission": submission}

        if field.question.input_type == PollInputType.TEXT:
            answer_payload["text_value"] = fake.sentence()
        elif q.input_type == PollInputType.NUMBER:
            answer_payload["number_value"] = random.randint(
                q.number_input.min_value, q.number_input.max_value
            )
        elif q.input_type == PollInputType.SCALE:
            answer_payload["number_value"] = random.randint(
                q.scale_input.min_value, q.scale_input.max_value
            )
        elif q.input_type == PollInputType.CHOICE:
            answer_payload["choice_value"] = random.sample(list(q.choice_input.options.all()), 1)

        PollQuestionAnswer.objects.create(**answer_payload)

    return submission
