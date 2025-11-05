from clubs.tests.utils import create_test_club
from core.abstracts.tests import TestsBase
from lib.faker import fake
from rest_framework import exceptions

from polls.models import (
    Poll,
    PollField,
    PollInputType,
    PollQuestion,
    PollUserFieldType,
    TextInput,
)
from polls.tests.utils import create_test_poll, create_test_pollquestion


class PollModelTests(TestsBase):
    """Basic tests for poll models."""

    def test_create_poll(self):
        """Should create a new poll with fields."""

        club = create_test_club()
        poll = Poll.objects.create(
            club=club, name=fake.title(), description=fake.paragraph()
        )
        initial_input_count = TextInput.objects.count()

        field = PollField.objects.create(poll=poll, order=0)
        PollQuestion.objects.create(
            field=field,
            label="Example question",
            input_type=PollInputType.TEXT,
            create_input=True,
        )

        self.assertEqual(TextInput.objects.count(), initial_input_count + 1)

    def test_raise_error_duplicate_user_fields(self):
        """Should raise error if multiple questions link to the same user field."""

        poll = create_test_poll()
        create_test_pollquestion(poll, link_user_field=PollUserFieldType.NAME)

        with self.assertRaises(exceptions.ValidationError):
            create_test_pollquestion(poll, link_user_field=PollUserFieldType.NAME)
