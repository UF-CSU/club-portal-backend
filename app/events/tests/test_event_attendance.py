from clubs.tests.utils import create_test_club
from core.abstracts.tests import PublicApiTestsBase
from events.models import EventAttendance
from events.tests.utils import create_test_event, event_attendance_list_url
from lib.faker import fake
from polls.models import Poll, PollField, PollInputType, PollQuestion, PollSubmission
from users.models import User
from users.tests.utils import create_test_user


class EventAttendancePublicTests(PublicApiTestsBase):
    """Test recording event attendance via api."""

    def setUp(self):
        super().setUp()

        self.user = create_test_user()

        self.primary_club = create_test_club()
        self.secondary_club = create_test_club()
        self.event = create_test_event(
            host=self.primary_club, secondary_hosts=[self.secondary_club]
        )
        self.url = event_attendance_list_url(self.event.pk)

        self.required_user_fields_for_create = {
            # TODO: Add other user fields required for submission
        }

    def assertUserNotAttendedEvent(self, user=None, event=None):
        """EventAttendance object should NOT have been created."""

        user = user or self.user
        event = event or self.event

        self.assertEqual(
            EventAttendance.objects.filter(event=event, user=user).count(), 0
        )

    def assertUserAttendedEvent(self, user=None, event=None, attendance_count=1):
        """EventAttendance object should have been created."""

        user = user or self.user
        event = event or self.event

        self.assertEqual(
            EventAttendance.objects.filter(event=event, user=user).count(),
            attendance_count,
        )

    def assertValidSubmission(self, question: PollQuestion, user=None, text_value="MD"):
        """Poll submission should be correct."""

        user = user or self.user

        submission = PollSubmission.objects.get(poll=question.field.poll, user=user)
        self.assertEqual(
            submission.answers.get(question__id=question.pk).text_value,
            text_value,
        )

        return submission

    def assertNoPollSubmission(self, question: PollQuestion, user=None):
        """There should be no poll submission for user."""

        user = user or self.user

        self.assertFalse(
            PollSubmission.objects.filter(poll=question.field.poll, user=user).exists()
        )

    def create_event_poll(self, require_submission: bool = True):
        """Create mock poll for event."""

        poll = Poll.objects.create(name="Test poll", event=self.event)
        field = PollField.objects.create(poll, order=0)
        # This would probably be a choice field, but use text for simplicity
        question = PollQuestion.objects.create(
            field=field,
            label="Shirt size",
            input_type=PollInputType.TEXT,
            create_input=True,
        )

        self.event.is_poll_submission_required = require_submission
        self.event.save()

        return poll, field, question

    def test_user_attend_event_no_poll(self):
        """
        Should record user attendance if no poll.

        CASE: 1

        - User logged in: yes
        - Profile completed: yes
        - Event has poll: no
        - Poll required: no
        """

        self.client.force_authenticate(self.user)

        payload = {}
        res = self.client.post(self.url, payload)
        self.assertResCreated(res)

        # Verify attendance created
        self.assertEqual(EventAttendance.objects.count(), 1)

        # TODO: Should the user be added to the club?

    def test_user_attend_event_update_profile(self):
        """
        Should record user attendance if need to update profile.

        CASE: 2

        - User logged in: yes
        - Profile completed: no
        - Event has poll: no
        - Poll required: no
        """

        self.user = create_test_user(name=None)
        self.client.force_authenticate(self.user)

        # Allow attendance if updating profile
        payload = {
            "user": {"email": self.user.email, "profile": {"name": fake.name()}},
        }
        res = self.client.post(self.url, payload, format="json")
        self.assertResCreated(res)

        self.assertEqual(EventAttendance.objects.count(), 1)
        self.user.refresh_from_db()
        self.assertEqual(self.user.name, payload["user"]["profile"]["name"])

    def test_guest_attend_event(self):
        """
        Should record user attendance, update or create user.

        CASE: 3

        - User logged in: no
        - Profile completed: yes/no
        - Event has poll: no
        - Poll required: no
        """

        # Try, but fail, to record attendance
        payload = {}
        res = self.client.post(self.url, payload)
        self.assertResBadRequest(res)
        self.assertUserNotAttendedEvent()

        # Should create user
        payload = {
            "user": {
                "email": fake.safe_email(),
                **self.required_user_fields_for_create,
                "profile": {"name": fake.name()},
            },
        }
        res = self.client.post(self.url, payload, format="json")
        self.assertResCreated(res)

        self.assertEqual(User.objects.count(), 2)
        user = User.objects.get(email=payload["user"]["email"])
        self.assertUserAttendedEvent(user=user)

        # Should update user
        payload = {
            "user": {"email": self.user.email, "profile": {"name": fake.name()}},
        }
        res = self.client.post(self.url, payload, format="json")
        self.assertResCreated(res)

        self.assertEqual(User.objects.count(), 2)
        self.assertUserAttendedEvent()
        self.user.refresh_from_db()
        self.assertEqual(self.user.name, payload["user"]["profile"]["name"])

    def test_user_attends_event_submits_poll(self):
        """
        Should record event attendance and poll submission.

        CASE: 4

        - User logged in: yes
        - Profile completed: yes
        - Event has poll: yes
        - Poll required: no
        """

        self.client.force_authenticate(self.user)
        p, f, q = self.create_event_poll(require_submission=False)

        # Without submission
        payload = {}
        res = self.client.post(self.url, payload)
        self.assertResCreated(res)
        self.assertUserAttendedEvent()

        EventAttendance.objects.all().delete()

        # With submission
        payload = {
            "poll_submission": {
                "answers": [
                    {"question": q.pk, "text_value": "MD"},
                ],
            },
        }
        res = self.client.post(self.url, payload, format="json")
        self.assertResCreated(res)
        self.assertUserAttendedEvent()
        self.assertValidSubmission(q, text_value="MD")

    def test_user_attends_event_require_poll(self):
        """
        Should create attendance if poll is required.

        CASE: 5

        - User logged in: yes
        - Profile completed: yes
        - Event has poll: yes
        - Poll required: yes
        """

        self.client.force_authenticate(self.user)
        p, f, q = self.create_event_poll(require_submission=True)

        # Attempt, but fail, to attend event
        payload = {}
        res = self.client.post(self.url, payload)
        self.assertResBadRequest(res)
        self.assertUserNotAttendedEvent()

        # With submission
        payload = {
            "poll_submission": {
                "answers": [
                    {"question": q.pk, "text_value": "MD"},
                ],
            },
        }
        res = self.client.post(self.url, payload, format="json")
        self.assertResCreated(res)
        self.assertUserAttendedEvent()
        self.assertValidSubmission(q, text_value="MD")

    def test_guest_attends_event_require_poll(self):
        """
        Should record event attendance and poll submission for guest.
        CASE: 6

        - User logged in: no
        - Profile completed: yes/no
        - Event has poll: yes
        - Poll required: yes
        """

        p, f, q = self.create_event_poll(require_submission=True)

        # Create new user
        payload = {
            "user": {
                "email": fake.safe_email(),
                **self.required_user_fields_for_create,
                "profile": {"name": fake.name()},
            },
            "poll_submission": {
                "answers": [
                    {"question": q.pk, "text_value": "MD"},
                ],
            },
        }
        res = self.client.post(self.url, payload, format="json")
        self.assertResCreated(res)
        self.assertEqual(User.objects.count(), 2)
        user = User.objects.get(email=payload["user"]["email"])
        self.assertUserAttendedEvent(user=user)
        self.assertValidSubmission(q, user=user, text_value="MD")

        # Has completed profile, update fields
        payload = {
            "user": {"email": self.user.email, "profile": {"name": fake.name()}},
            "poll_submission": {
                "answers": [
                    {"question": q.pk, "text_value": "MD"},
                ],
            },
        }
        res = self.client.post(self.url, payload, format="json")
        self.assertResCreated(res)
        self.assertEqual(User.objects.count(), 2)
        self.assertUserAttendedEvent()
        self.user.refresh_from_db()
        self.assertEqual(self.user.name, payload["user"]["profile"]["name"])
        EventAttendance.objects.all().delete()
        PollSubmission.objects.all().delete()

        # Not completed profile, raise error
        payload = {
            "user": {
                "email": fake.safe_email(),
            },
            "poll_submission": {
                "answers": [
                    {"question": q.pk, "text_value": "MD"},
                ],
            },
        }
        res = self.client.post(self.url, payload, format="json")
        self.assertResBadRequest(res)
        self.assertNoPollSubmission(q)

        # Not completed profile, update fields
        payload = {
            "user": {"email": self.user.email, "profile": {"name": fake.name()}},
            "poll_submission": {
                "answers": [
                    {"question": q.pk, "text_value": "MD"},
                ],
            },
        }
        res = self.client.post(self.url, payload, format="json")
        self.assertResCreated(res)
        self.assertUserAttendedEvent()
        self.assertValidSubmission(q)
        self.user.refresh_from_db()
        self.assertEqual(self.user.name, payload["user"]["profile"]["name"])

    def test_multi_step_form_submission(self):
        """
        Should record event attendance, then poll submission.

        CASE: 7

        - User logged in: no
        - Profile completed: no
        - Event has poll: yes
        - Poll required: no
        """

        p, f, q = self.create_event_poll(require_submission=False)

        # Step 1: Record user
        payload = {
            "user": {"email": fake.safe_email(), "profile": {"name": fake.name()}},
        }
        res = self.client.post(self.url, payload, format="json")
        self.assertResCreated(res)
        data = res.json()
        self.assertIsNotNone(data["user"]["email"])
        user_email = data["user"]["email"]
        user = User.objects.get(email=user_email)

        # Step 2: Record poll submission
        payload = {
            "user": {
                "email": user.email,
            },
            "poll_submission": {
                "answers": [
                    {"question": q.pk, "text_value": "MD"},
                ],
            },
        }
        res = self.client.post(self.url, payload, format="json")
        self.assertResCreated(res)
        self.assertUserAttendedEvent(user=user, attendance_count=1)
        self.assertValidSubmission(q, user=user, text_value="MD")
