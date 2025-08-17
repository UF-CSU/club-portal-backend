from clubs.tests.utils import create_test_club
from core.abstracts.tests import PrivateApiTestsBase, PublicApiTestsBase
from events.models import EventAttendance
from events.tests.utils import create_test_event
from polls.models import (
    Poll,
    PollInputType,
    PollQuestion,
    PollSubmission,
    PollUserFieldType,
)
from polls.tests.test_poll_views import pollsubmission_list_url
from polls.tests.utils import create_test_pollquestion
from users.models import User
from users.tests.utils import create_test_user


class AttendancePublicTests(PublicApiTestsBase):
    """Test recording event attendance via api."""

    def setUp(self):
        super().setUp()

        self.user = create_test_user(email="user@example.com")

        self.primary_club = create_test_club()
        self.secondary_club = create_test_club()
        self.event = create_test_event(
            host=self.primary_club,
            secondary_hosts=[self.secondary_club],
            enable_attendance=True,
        )

        self.poll: Poll = self.event.poll
        self.email_q = self.poll.questions.get(is_user_lookup=True)

        self.url = pollsubmission_list_url(self.poll.pk)

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

    def assertUserSubmittedAnswer(
        self, question: PollQuestion, user=None, text_value="MD"
    ):
        """Poll submission should be correct."""

        user = user or self.user

        submission = PollSubmission.objects.get(poll=question.field.poll, user=user)
        self.assertEqual(
            submission.answers.get(question__id=question.pk).text_value,
            text_value,
        )

        return submission

    def assertUserNotSubmittedPoll(self, question: PollQuestion, user=None):
        """There should be no poll submission for user."""

        user = user or self.user

        self.assertFalse(
            PollSubmission.objects.filter(poll=question.field.poll, user=user).exists()
        )

    #####################################################
    # Event/Poll Submission Tests
    #####################################################

    def test_user_attend_event(self):
        """Should allow authenticated user to attend event."""

        self.client.force_authenticate(self.user)

        payload = {}
        res = self.client.post(self.url, payload)
        self.assertResCreated(res)
        self.assertUserAttendedEvent()

    def test_user_finish_profile(self):
        """Should populate user's profile with poll answer."""

        # Setup fields
        name_q = create_test_pollquestion(
            self.poll, link_user_field=PollUserFieldType.NAME
        )
        phone_q = create_test_pollquestion(
            self.poll, link_user_field=PollUserFieldType.PHONE
        )
        major_q = create_test_pollquestion(
            self.poll,
            input_type=PollInputType.CHOICE,
            link_user_field=PollUserFieldType.MAJOR,
        )
        major_q.choice_input.is_multiple = False
        major_q.choice_input.save()
        major_q.choice_input.options.create(label="Computer Science")

        minor_q = create_test_pollquestion(
            self.poll,
            input_type=PollInputType.CHOICE,
            link_user_field=PollUserFieldType.MINOR,
        )
        minor_q.choice_input.is_multiple = True
        minor_q.choice_input.save()
        minor_q.choice_input.options.create(label="Mathematics")
        minor_q.choice_input.options.create(label="Art")

        college_q = create_test_pollquestion(
            self.poll, link_user_field=PollUserFieldType.COLLEGE
        )

        # API Request
        self.client.force_authenticate(self.user)
        self.assertNotEqual(self.user.profile.name, "John Doe")

        payload = {
            "answers": [
                {"question": name_q.pk, "text_value": "John Doe"},
                {"question": phone_q.pk, "text_value": "123-456-7890"},
                {"question": major_q.pk, "options_value": ["Computer Science"]},
                {"question": minor_q.pk, "options_value": ["Mathematics", "Art"]},
                {"question": college_q.pk, "text_value": "Engineering"},
            ],
        }
        res = self.client.post(self.url, payload)
        self.assertResCreated(res)

        self.user.refresh_from_db()
        self.assertUserAttendedEvent()
        self.assertUserSubmittedAnswer(name_q, text_value="John Doe")
        self.assertEqual(self.user.profile.name, "John Doe")
        self.assertEqual(self.user.profile.phone, "123-456-7890")
        self.assertEqual(self.user.profile.major, "Computer Science")
        self.assertEqual(self.user.profile.minor, "Mathematics, Art")
        self.assertEqual(self.user.profile.college, "Engineering")

    def test_allow_user_skip_profile_fields(self):
        """Should allow a user to skip a profile field that they already have."""

        create_test_pollquestion(self.poll, is_required=True)
        self.user.profile.name = "John Doe"
        self.user.profile.save()
        self.client.force_authenticate(self.user)

        payload = {}
        res = self.client.post(self.url, payload)
        self.assertResCreated(res)
        self.assertUserAttendedEvent()
        self.user.refresh_from_db()
        self.assertEqual(self.user.profile.name, "John Doe")

    def test_new_guest_user_attend_event(self):
        """Should allow guest users to attend an event."""

        name_q = create_test_pollquestion(
            self.poll, link_user_field=PollUserFieldType.NAME
        )
        shirt_q = create_test_pollquestion(self.poll)

        payload = {
            "answers": [
                {"question": self.email_q.pk, "text_value": "user2@example.com"},
                {"question": name_q.pk, "text_value": "Alex Smith"},
                {"question": shirt_q.pk, "text_value": "MD"},
            ]
        }
        res = self.client.post(self.url, payload)
        self.assertResCreated(res)
        self.assertTrue(User.objects.filter(email="user2@example.com"))
        user = User.objects.get(email="user2@example.com")
        self.assertEqual(user.profile.name, "Alex Smith")

        self.assertUserAttendedEvent(user)
        self.assertUserSubmittedAnswer(name_q, user, text_value="Alex Smith")
        self.assertUserSubmittedAnswer(shirt_q, user, text_value="MD")

    def test_returning_guest_user_attend_event(self):
        """Should allow existing to register as a guest."""

        name_q = create_test_pollquestion(
            self.poll, link_user_field=PollUserFieldType.NAME
        )
        shirt_q = create_test_pollquestion(self.poll)

        self.assertNotEqual(self.user.profile.name, "Alex Smith")

        payload = {
            "answers": [
                {"question": self.email_q.pk, "text_value": self.user.email},
                {"question": name_q.pk, "text_value": "Alex Smith"},
                {"question": shirt_q.pk, "text_value": "MD"},
            ]
        }
        res = self.client.post(self.url, payload)
        self.assertResCreated(res)
        self.assertEqual(User.objects.count(), 1)
        self.user.refresh_from_db()

        self.assertUserAttendedEvent(self.user)
        self.assertUserSubmittedAnswer(name_q, self.user, text_value="Alex Smith")
        self.assertUserSubmittedAnswer(shirt_q, self.user, text_value="MD")
        self.assertEqual(self.user.profile.name, "Alex Smith")

    def test_returning_guest_uses_school_email(self):
        """Should allow a returning guest use their school email to register for an event."""

        name_q = create_test_pollquestion(
            self.poll, link_user_field=PollUserFieldType.NAME
        )
        shirt_q = create_test_pollquestion(self.poll)

        self.assertNotEqual(self.user.profile.name, "Alex Smith")
        self.user.profile.school_email = "alex@ufl.edu"
        self.user.profile.save()

        payload = {
            "answers": [
                {"question": self.email_q.pk, "text_value": "alex@ufl.edu"},
                {"question": name_q.pk, "text_value": "Alex Smith"},
                {"question": shirt_q.pk, "text_value": "MD"},
            ]
        }
        res = self.client.post(self.url, payload)
        self.assertResCreated(res)
        self.assertEqual(User.objects.count(), 1)
        self.user.refresh_from_db()

        self.assertUserAttendedEvent(self.user)
        self.assertUserSubmittedAnswer(name_q, self.user, text_value="Alex Smith")
        self.assertUserSubmittedAnswer(shirt_q, self.user, text_value="MD")
        self.assertEqual(self.user.profile.name, "Alex Smith")

    def test_guest_must_provide_email(self):
        """Should raise error if guest tries to submit without giving their email."""

        name_q = create_test_pollquestion(
            self.poll, link_user_field=PollUserFieldType.NAME
        )

        payload = {
            "answers": [
                {"question": name_q.pk, "text_value": "Alex Smith"},
            ]
        }
        res = self.client.post(self.url, payload)
        self.assertResBadRequest(res)
        self.assertEqual(PollSubmission.objects.count(), 0)
        self.assertEqual(User.objects.count(), 1)
        self.assertNotEqual(self.user.profile.name, "Alex Smith")

    def test_user_multiple_submissions(self):
        """When a user submits multiple times, it should only save once."""

        self.client.force_authenticate(self.user)
        shirt_q = create_test_pollquestion(self.poll)
        name_q = create_test_pollquestion(
            self.poll, link_user_field=PollUserFieldType.NAME
        )

        # Submission 1
        payload = {
            "answers": [
                {"question": name_q.pk, "text_value": "Alex Smith"},
                {"question": shirt_q.pk, "text_value": "MD"},
            ]
        }
        res = self.client.post(self.url, payload)
        self.assertResCreated(res)

        self.user.refresh_from_db()
        self.assertEqual(self.user.profile.name, "Alex Smith")
        self.assertUserSubmittedAnswer(shirt_q, text_value="MD")

        # Submission 2
        payload = {
            "answers": [
                {"question": name_q.pk, "text_value": "John Doe"},
                {"question": shirt_q.pk, "text_value": "LG"},
            ]
        }
        res = self.client.post(self.url, payload)
        self.assertResCreated(res)
        self.user.refresh_from_db()

        self.assertEqual(PollSubmission.objects.count(), 1)
        self.assertEqual(self.user.profile.name, "John Doe")
        self.assertUserSubmittedAnswer(shirt_q, text_value="LG")


class AttendancePrivateTests(PrivateApiTestsBase):
    """Test managing attendance as authenticated user."""

    # # TODO: Implement user submission retrieval
    # def test_user_retrieve_submission(self):
    #     """Should return user's poll submission if queried."""

    #     shirt_q = create_test_pollquestion(self.poll)

    #     # Another user
    #     payload = {
    #         "answers": [
    #             {"question": self.email_q.pk, "text_value": "user2@example.com"},
    #             {"question": shirt_q.pk, "text_value": "SM"},
    #         ]
    #     }
    #     res = self.client.post(self.url, payload)
    #     self.assertResCreated(res)
    #     self.assertEqual(User.objects.count(), 2)

    #     # Current user submits form
    #     self.client.force_authenticate(self.user)
    #     payload = {
    #         "answers": [
    #             {"question": shirt_q.pk, "text_value": "MD"},
    #         ]
    #     }
    #     res = self.client.post(self.url, payload)
    #     self.assertResCreated(res)
    #     self.assertEqual(PollSubmission.objects.count(), 2)

    #     # Current user retrieves own submission only
    #     res = self.client.get(self.url)
    #     self.assertResOk(res)
    #     data = res.json()
    #     self.assertLength(data, 1)
