from clubs.tests.utils import create_test_club
from core.abstracts.tests import TestsBase
from lib.faker import fake
from rest_framework import exceptions

from polls.models import (
    Poll,
    PollField,
    PollInputType,
    PollQuestion,
    PollType,
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

    def test_private_poll_no_club_raises_error(self):
        """Should raise error when setting a poll without a club as private."""

        poll = create_test_poll(poll_type=PollType.TEMPLATE, force_club_none=True)
        self.assertIsNone(poll.club)

        with self.assertRaises(exceptions.ValidationError):
            poll.is_private = True
            poll.save()

    def test_raise_error_on_invalid_required_role(self):
        """Should raise error if required role is set to a club other than assigned club."""

        c1 = create_test_club()
        c2 = create_test_club()

        p0 = create_test_poll()
        p1 = create_test_poll(club=c1)

        # Raise error when club not set
        with self.assertRaises(exceptions.ValidationError):
            p0.allowed_club_roles.set([c1.roles.get(is_default=True)])
            p0.save()

        # Raise error when setting other club's role
        with self.assertRaises(exceptions.ValidationError):
            p1.allowed_club_roles.set([c2.roles.get(is_default=True)])
            p1.save()
