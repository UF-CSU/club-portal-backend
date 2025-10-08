from unittest.mock import patch

import pytz
from django.utils import timezone

from core.abstracts.tests import PeriodicTaskTestsBase, TestsBase
from polls.models import Poll, PollStatusType, PollTemplate
from polls.services import PollService, PollTemplateService
from polls.tests.utils import (
    create_test_poll,
    create_test_pollquestion,
    create_test_pollsubmission,
)


class PollServiceTests(PeriodicTaskTestsBase):
    """Unit tests for poll services."""

    def assertOpenDatesSynced(self, poll: Poll):
        """Poll's `open_at` field should equal time on open periodic task."""

        self.assertFalse(poll.are_tasks_out_of_sync)

        if poll.open_at is not None:
            self.assertIsNotNone(poll.open_task)
            self.assertEqual(poll.open_at, poll.open_task.clocked.clocked_time)
        else:
            self.assertIsNone(poll.open_task)

    def assertCloseDatesSynced(self, poll: Poll):
        """Poll's `open_at` field should equal time on open periodic task."""

        self.assertFalse(poll.are_tasks_out_of_sync)

        if poll.close_at is not None:
            self.assertIsNotNone(poll.close_task)
            self.assertEqual(poll.close_at, poll.close_task.clocked.clocked_time)
        else:
            self.assertIsNone(poll.close_task)

    def assertDatesSynced(self, poll: Poll):
        """Check `open_at` and `close_at` dates are synced."""

        self.assertOpenDatesSynced(poll)
        self.assertCloseDatesSynced(poll)

    def test_set_poll_open_at(self):
        """Setting poll open date should change status to scheduled."""

        poll = create_test_poll()
        self.assertEqual(poll.status, PollStatusType.DRAFT)
        self.assertDatesSynced(poll)

        # Publish poll
        poll.is_published = True
        poll.save()
        self.assertEqual(poll.status, PollStatusType.OPEN)
        self.assertIsNone(poll.open_task)
        self.assertIsNone(poll.close_task)

        # Test setting to future date
        poll.open_at = timezone.now() + timezone.timedelta(days=1)
        poll.save()
        poll.refresh_from_db()
        self.assertEqual(poll.status, PollStatusType.SCHEDULED)
        self.assertDatesSynced(poll)

        # Test setting to past date
        poll.open_at = timezone.now() - timezone.timedelta(days=1)
        poll.save()
        poll.refresh_from_db()
        self.assertEqual(poll.status, PollStatusType.OPEN)
        self.assertDatesSynced(poll)

        # Test setting close date
        poll.close_at = timezone.now() - timezone.timedelta(hours=1)
        poll.save()
        poll.refresh_from_db()
        self.assertEqual(poll.status, PollStatusType.CLOSED)
        self.assertDatesSynced(poll)

    def test_poll_scheduling(self):
        """Periodic tasks should be created when setting open/close dates."""

        poll = create_test_poll()
        self.assertIsNone(poll.open_task)
        self.assertIsNone(poll.close_task)
        poll.is_published = True
        poll.save()
        poll.refresh_from_db()

        # Setting open, not closed
        poll.open_at = timezone.now() + timezone.timedelta(days=1)
        poll.save()
        poll.refresh_from_db()
        self.assertIsNotNone(poll.open_at)
        self.assertIsNone(poll.close_at)
        self.assertDatesSynced(poll)
        self.assertEqual(poll.status, PollStatusType.SCHEDULED)

        # Changing open time
        poll.open_at = timezone.now() + timezone.timedelta(days=1)
        poll.save()
        poll.refresh_from_db()
        self.assertDatesSynced(poll)
        self.assertEqual(poll.status, PollStatusType.SCHEDULED)

        # Removing open time
        poll.open_at = None
        poll.save()
        poll.refresh_from_db()
        self.assertDatesSynced(poll)
        self.assertEqual(poll.status, PollStatusType.OPEN)

    @patch("django.utils.timezone.now")
    def test_poll_scheduled_task(self, timezone_now):
        """Should set poll to open or close after a delay."""

        timezone_now.return_value = timezone.datetime.now(tz=pytz.utc)

        poll = create_test_poll()
        poll.is_published = True
        poll.open_at = timezone.now() + timezone.timedelta(days=1)
        poll.close_at = timezone.now() + timezone.timedelta(days=2)
        poll.save()
        poll.refresh_from_db()

        self.assertIsNotNone(poll.open_task)
        self.assertIsNotNone(poll.close_task)
        self.assertEqual(poll.status, PollStatusType.SCHEDULED)

        # Set time to be within poll open time
        timezone_now.return_value = timezone.datetime.now(
            tz=pytz.utc
        ) + timezone.timedelta(days=1, hours=1)

        # Check running open task
        self.assertRunPeriodicTask(
            poll.open_task, check_params={"status": PollStatusType.OPEN}
        )
        poll.refresh_from_db()
        self.assertEqual(poll.status, PollStatusType.OPEN)

        # Set time to be after poll open time
        timezone_now.return_value = timezone.datetime.now(
            tz=pytz.utc
        ) + timezone.timedelta(days=2, hours=1)

        # Check running close task
        self.assertRunPeriodicTask(
            poll.open_task, check_params={"status": PollStatusType.OPEN}
        )
        poll.refresh_from_db()
        self.assertEqual(poll.status, PollStatusType.CLOSED)

    def test_poll_submissions_df(self):
        """Should convert submissions to a dataframe."""

        QUESTION_COUNT = 3
        SUBMISSION_COUNT = 10

        # + user_id, user_email, user_school_email, date
        SUBMISSION_COL_COUNT = QUESTION_COUNT + 4

        # Create form
        poll = create_test_poll()
        initial_question_count = poll.questions.count()

        for i in range(QUESTION_COUNT):
            create_test_pollquestion(poll, label=f"Question {i + 1}")

        # Create submission
        for _i in range(SUBMISSION_COUNT):
            create_test_pollsubmission(poll)

        # Sanity checks
        poll.refresh_from_db()
        self.assertEqual(poll.fields.count(), initial_question_count + QUESTION_COUNT)
        self.assertEqual(poll.submissions.count(), SUBMISSION_COUNT)

        service = PollService(poll)
        df = service.get_submissions_df()
        self.assertEqual(len(df), SUBMISSION_COUNT)
        self.assertEqual(len(df.columns), SUBMISSION_COL_COUNT)


class PollTemplateServiceTests(TestsBase):
    """Unit tests for the poll template service."""

    def setUp(self):
        super().setUp()

        self.tpl = PollTemplate.objects.create(
            poll_name="Example Poll", template_name="Test Template"
        )
        self.service = PollTemplateService(self.tpl)

    # def test_create_poll(self):
    #     """Should create new poll from template."""

    #     # Setup fields
    #     f1 = PollField.objects.create(poll=self.tpl, order=1)
    #     f2 = PollField.objects.create(poll=self.tpl, order=2)

    #     expected_q1 = PollQuestion.objects.create(
    #         field=f1,
    #         label=fake.sentence(),
    #         input_type=PollInputType.TEXT,
    #         create_input=True,
    #     )
    #     expected_q2 = PollQuestion.objects.create(
    #         field=f2,
    #         label=fake.sentence(),
    #         input_type=PollInputType.TEXT,
    #         create_input=True,
    #     )

    #     # Generate poll
    #     poll = self.service.create_poll()
    #     self.assertIsNotNone(poll)
    #     self.assertEqual(poll.fields.count(), 2)
    #     self.assertEqual(PollField.objects.count(), 4)

    #     self.assertEqual(poll.fields.get(order=1).question.label, expected_q1.label)
    #     self.assertEqual(poll.fields.get(order=2).question.label, expected_q2.label)
