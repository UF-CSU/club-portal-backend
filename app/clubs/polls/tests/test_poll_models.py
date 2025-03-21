from clubs.polls.models import Poll, PollField, PollInputType, PollQuestion, TextInput
from core.abstracts.tests import TestsBase
from lib.faker import fake


class PollModelTests(TestsBase):
    """Basic tests for poll models."""

    def test_create_poll(self):
        """Should create a new poll with fields."""

        poll = Poll.objects.create(name=fake.title(), description=fake.paragraph())
        field = PollField.objects.create(poll=poll, order=0)
        PollQuestion.objects.create(
            field=field,
            label="Example question",
            input_type=PollInputType.TEXT,
            create_input=True,
        )

        self.assertEqual(TextInput.objects.count(), 1)
