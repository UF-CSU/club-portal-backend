from django.utils import timezone

from clubs.services import ClubService
from clubs.tests.utils import create_test_club
from core.abstracts.tests import PrivateApiTestsBase, PublicApiTestsBase
from events.models import EventAttendance
from events.tests.utils import create_test_event, event_attendance_list_url
from lib.faker import fake
from polls.models import Poll, PollQuestion, PollSubmission, PollUserFieldType
from polls.tests.test_poll_views import pollsubmission_list_url
from polls.tests.utils import create_test_pollquestion
from users.models import User
from users.tests.utils import create_test_user, create_test_users


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
        self.url = pollsubmission_list_url(self.event.pk)

        self.poll: Poll = self.event.poll
        self.email_q = self.poll.questions.get(is_user_lookup=True)
        # self.question = create_test_pollquestion(self.poll, label="Shirt size")

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

        name_q = create_test_pollquestion(
            self.poll, link_user_field=PollUserFieldType.NAME
        )
        self.client.force_authenticate(self.user)
        self.assertNotEqual(self.user.profile.name, "John Doe")

        payload = {
            "answers": [
                {"question": name_q.pk, "text_value": "John Doe"},
            ]
        }
        res = self.client.post(self.url, payload)
        self.assertResCreated(res)

        self.user.refresh_from_db()
        self.assertUserAttendedEvent()
        self.assertUserSubmittedAnswer(name_q, text_value="John Doe")
        self.assertEqual(self.user.profile.name, "John Doe")

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
                {"question": self.email_q.pk, "answer": "user2@example.com"},
                {"question": name_q.pk, "answer": "Alex Smith"},
                {"question": shirt_q.pk, "answer": "MD"},
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
                {"question": self.email_q.pk, "answer": self.user.email},
                {"question": name_q.pk, "answer": "Alex Smith"},
                {"question": shirt_q.pk, "answer": "MD"},
            ]
        }
        res = self.client.post(self.url, payload)
        self.assertResCreated(res)
        self.assertEqual(User.objects.count(), 1)
        self.assertEqual(self.user.profile.name, "Alex Smith")

        self.assertUserAttendedEvent(self.user)
        self.assertUserSubmittedAnswer(name_q, self.user, text_value="Alex Smith")
        self.assertUserSubmittedAnswer(shirt_q, self.user, text_value="MD")

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
                {"question": self.email_q.pk, "answer": "alex@ufl.edu"},
                {"question": name_q.pk, "answer": "Alex Smith"},
                {"question": shirt_q.pk, "answer": "MD"},
            ]
        }
        res = self.client.post(self.url, payload)
        self.assertResCreated(res)
        self.assertEqual(User.objects.count(), 1)
        self.assertEqual(self.user.profile.name, "Alex Smith")

        self.assertUserAttendedEvent(self.user)
        self.assertUserSubmittedAnswer(name_q, self.user, text_value="Alex Smith")
        self.assertUserSubmittedAnswer(shirt_q, self.user, text_value="MD")

    def test_guest_must_provide_email(self):
        """Should raise error if guest tries to submit without giving their email."""

        name_q = create_test_pollquestion(
            self.poll, link_user_field=PollUserFieldType.NAME
        )

        payload = {
            "answers": [
                {"question": name_q.pk, "answer": "Alex Smith"},
            ]
        }
        res = self.client.post(self.url, payload)
        self.assertResBadRequest(res)
        self.assertEqual(PollSubmission.objects.count(), 0)
        self.assertEqual(User.objects.count(), 1)
        self.assertNotEqual(self.user.profile.name, "Alex Smith")

    def test_user_retrieve_submission(self):
        """Should return user's poll submission if queried."""

        shirt_q = create_test_pollquestion(self.poll)

        # Another user
        payload = {
            "answers": [
                {"question": self.email_q.pk, "text_value": "user2@example.com"},
                {"question": shirt_q.pk, "answer": "SM"},
            ]
        }
        res = self.client.post(self.url, payload)
        self.assertResCreated(res)
        self.assertEqual(User.objects.count(), 2)

        # Current user submits form
        self.client.force_authenticate(self.user)
        payload = {
            "answers": [
                {"question": shirt_q.pk, "answer": "MD"},
            ]
        }
        res = self.client.post(self.url, payload)
        self.assertResCreated(res)
        self.assertEqual(PollSubmission.objects.count(), 2)

        # Current user retrieves own submission only
        res = self.client.get(self.url)
        self.assertResOk(res)
        data = res.json()
        self.assertLength(data, 1)

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
                {"question": name_q.pk, "answer": "Alex Smith"},
                {"question": shirt_q.pk, "answer": "MD"},
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
                {"question": name_q.pk, "answer": "John Doe"},
                {"question": shirt_q.pk, "answer": "LG"},
            ]
        }
        res = self.client.post(self.url, payload)
        self.assertResCreated(res)
        self.user.refresh_from_db()

        self.assertEqual(PollSubmission.objects.count(), 1)
        self.assertEqual(self.user.profile.name, "John Doe")
        self.assertUserSubmittedAnswer(shirt_q, text_value="LG")

    # def test_user_attend_event_no_poll(self):
    #     """
    #     Should record user attendance if no poll.

    #     CASE: 1

    #     - User logged in: yes
    #     - Profile completed: yes
    #     - Event has poll: no
    #     """

    #     self.client.force_authenticate(self.user)

    #     payload = {}
    #     res = self.client.post(self.url, payload)
    #     self.assertResCreated(res)

    #     # Verify attendance created
    #     self.assertEqual(EventAttendance.objects.count(), 1)

    #     # TODO: Should the user be added to the club?

    # def test_user_attend_event_update_profile(self):
    #     """
    #     Should record user attendance if need to update profile.

    #     CASE: 2

    #     - User logged in: yes
    #     - Profile completed: no
    #     - Event has poll: no
    #     """

    #     self.user = create_test_user(name=None)
    #     self.client.force_authenticate(self.user)
    #     name_q = create_test_pollquestion(self.poll)

    #     # Allow attendance if updating profile
    #     # payload = {
    #     #     "user": {"email": self.user.email, "profile": {"name": fake.name()}},
    #     # }
    #     payload = {
    #         "answers": {
    #             "question": name_q.pk,
    #             "text_value": fake.name(),
    #         }
    #     }
    #     res = self.client.post(self.url, payload, format="json")
    #     self.assertResCreated(res)

    #     self.assertEqual(EventAttendance.objects.count(), 1)
    #     self.user.refresh_from_db()
    #     self.assertEqual(self.user.name, payload["user"]["profile"]["name"])

    # def test_guest_attend_event(self):
    #     """
    #     Should record user attendance, update or create user.

    #     CASE: 3

    #     - User logged in: no
    #     - Profile completed: yes/no
    #     - Event has poll: no
    #     - Poll required: no
    #     """

    #     # Try, but fail, to record attendance
    #     payload = {}
    #     res = self.client.post(self.url, payload)
    #     self.assertResBadRequest(res)
    #     self.assertUserNotAttendedEvent()

    #     # Should create user
    #     payload = {
    #         "user": {
    #             "email": fake.safe_email(),
    #             **self.required_user_fields_for_create,
    #             "profile": {"name": fake.name()},
    #         },
    #     }
    #     res = self.client.post(self.url, payload, format="json")
    #     self.assertResCreated(res)

    #     self.assertEqual(User.objects.count(), 2)
    #     user = User.objects.get(email=payload["user"]["email"])
    #     self.assertUserAttendedEvent(user=user)

    #     # Should update user
    #     payload = {
    #         "user": {"email": self.user.email, "profile": {"name": fake.name()}},
    #     }
    #     res = self.client.post(self.url, payload, format="json")
    #     self.assertResCreated(res)

    #     self.assertEqual(User.objects.count(), 2)
    #     self.assertUserAttendedEvent()
    #     self.user.refresh_from_db()
    #     self.assertEqual(self.user.name, payload["user"]["profile"]["name"])

    # # def test_user_attends_event_submits_poll(self):
    # #     """
    # #     Should record event attendance and poll submission.

    # #     CASE: 4

    # #     - User logged in: yes
    # #     - Profile completed: yes
    # #     - Event has poll: yes
    # #     - Poll required: no
    # #     """

    # #     self.client.force_authenticate(self.user)
    # #     question = self.create_event_pollquestion(require_submission=False)

    # #     # Without submission
    # #     payload = {}
    # #     res = self.client.post(self.url, payload)
    # #     self.assertResCreated(res)
    # #     self.assertUserAttendedEvent()

    # #     EventAttendance.objects.all().delete()

    # #     # With submission
    # #     payload = {
    # #         "poll_submission": {
    # #             "answers": [
    # #                 {"question": question.pk, "text_value": "MD"},
    # #             ],
    # #         },
    # #     }
    # #     res = self.client.post(self.url, payload, format="json")
    # #     self.assertResCreated(res)
    # #     self.assertUserAttendedEvent()
    # #     self.assertValidSubmission(question, text_value="MD")

    # def test_user_attends_event_require_poll(self):
    #     """
    #     Should create attendance if poll is required.

    #     CASE: 5

    #     - User logged in: yes
    #     - Profile completed: yes
    #     - Event has poll: yes
    #     - Poll required: yes
    #     """

    #     self.client.force_authenticate(self.user)

    #     # Attempt, but fail, to attend event
    #     payload = {}
    #     res = self.client.post(self.url, payload)
    #     self.assertResBadRequest(res)
    #     self.assertUserNotAttendedEvent()

    #     # With submission
    #     payload = {
    #         "answers": [
    #             {"question": self.question.pk, "text_value": "MD"},
    #         ],
    #     }
    #     res = self.client.post(self.url, payload, format="json")
    #     self.assertResCreated(res)
    #     self.assertUserAttendedEvent()
    #     self.assertValidSubmission(q, text_value="MD")

    # def test_guest_attends_event_require_poll(self):
    #     """
    #     Should record event attendance and poll submission for guest.
    #     CASE: 6

    #     - User logged in: no
    #     - Profile completed: yes/no
    #     - Event has poll: yes
    #     - Poll required: yes
    #     """

    #     p, f, q = self.create_event_pollquestion(require_submission=True)

    #     # Create new user
    #     payload = {
    #         "user": {
    #             "email": fake.safe_email(),
    #             **self.required_user_fields_for_create,
    #             "profile": {"name": fake.name()},
    #         },
    #         "poll_submission": {
    #             "answers": [
    #                 {"question": q.pk, "text_value": "MD"},
    #             ],
    #         },
    #     }
    #     res = self.client.post(self.url, payload, format="json")
    #     self.assertResCreated(res)
    #     self.assertEqual(User.objects.count(), 2)
    #     user = User.objects.get(email=payload["user"]["email"])
    #     self.assertUserAttendedEvent(user=user)
    #     self.assertValidSubmission(q, user=user, text_value="MD")

    #     # Has completed profile, update fields
    #     payload = {
    #         "user": {"email": self.user.email, "profile": {"name": fake.name()}},
    #         "poll_submission": {
    #             "answers": [
    #                 {"question": q.pk, "text_value": "MD"},
    #             ],
    #         },
    #     }
    #     res = self.client.post(self.url, payload, format="json")
    #     self.assertResCreated(res)
    #     self.assertEqual(User.objects.count(), 2)
    #     self.assertUserAttendedEvent()
    #     self.user.refresh_from_db()
    #     self.assertEqual(self.user.name, payload["user"]["profile"]["name"])
    #     EventAttendance.objects.all().delete()
    #     PollSubmission.objects.all().delete()

    #     # Not completed profile, raise error
    #     payload = {
    #         "user": {
    #             "email": fake.safe_email(),
    #         },
    #         "poll_submission": {
    #             "answers": [
    #                 {"question": q.pk, "text_value": "MD"},
    #             ],
    #         },
    #     }
    #     res = self.client.post(self.url, payload, format="json")
    #     self.assertResBadRequest(res)
    #     self.assertNoPollSubmission(q)

    #     # Not completed profile, update fields
    #     payload = {
    #         "user": {"email": self.user.email, "profile": {"name": fake.name()}},
    #         "poll_submission": {
    #             "answers": [
    #                 {"question": q.pk, "text_value": "MD"},
    #             ],
    #         },
    #     }
    #     res = self.client.post(self.url, payload, format="json")
    #     self.assertResCreated(res)
    #     self.assertUserAttendedEvent()
    #     self.assertValidSubmission(q)
    #     self.user.refresh_from_db()
    #     self.assertEqual(self.user.name, payload["user"]["profile"]["name"])

    # def test_multi_step_form_submission(self):
    #     """
    #     Should record event attendance, then poll submission.

    #     CASE: 7

    #     - User logged in: no
    #     - Profile completed: no
    #     - Event has poll: yes
    #     - Poll required: no
    #     """

    #     p, f, q = self.create_event_pollquestion(require_submission=False)

    #     # Step 1: Record user
    #     payload = {
    #         "user": {"email": fake.safe_email(), "profile": {"name": fake.name()}},
    #     }
    #     res = self.client.post(self.url, payload, format="json")
    #     self.assertResCreated(res)
    #     data = res.json()
    #     self.assertIsNotNone(data["user"]["email"])
    #     user_email = data["user"]["email"]
    #     user = User.objects.get(email=user_email)

    #     # Step 2: Record poll submission
    #     payload = {
    #         "user": {
    #             "email": user.email,
    #         },
    #         "poll_submission": {
    #             "answers": [
    #                 {"question": q.pk, "text_value": "MD"},
    #             ],
    #         },
    #     }
    #     res = self.client.post(self.url, payload, format="json")
    #     self.assertResCreated(res)
    #     self.assertUserAttendedEvent(user=user, attendance_count=1)
    #     self.assertValidSubmission(q, user=user, text_value="MD")


class AttendanceEdgeCasesTests(PublicApiTestsBase):
    """Check various edge cases with attendance tracking."""

    def test_event_attendance_not_enabled(self):
        """Should not allow attendance if disabled."""

        event = create_test_event(enable_attendance=False)
        self.assertIsNone(event.poll)

        url = event_attendance_list_url(event.pk)
        payload = {
            "user": {"email": fake.safe_email(), "profile": {"name": fake.name()}},
        }
        res = self.client.post(url, payload, format="json")
        self.assertResBadRequest(res)


class AttendancePrivateTests(PrivateApiTestsBase):
    """Test admin interactions with event attendance data."""

    def create_authenticated_user(self):
        self.club = create_test_club()
        self.club_service = ClubService(self.club)

        user = create_test_user()
        self.membership = self.club_service.add_member(user, roles=["Officer"])
        return user

    def test_attendance_analytics_api(self):
        """Should return attendance analytics for an event."""

        event = create_test_event(
            host=self.club,
            start_at=timezone.now(),
            end_at=timezone.now() + timezone.timedelta(hours=2),
        )
        users = create_test_users(5)

        for user in users:
            EventAttendance.objects.create(user=user, event=event)

        self.assertEqual(EventAttendance.objects.count(), 5)

        # Check getting attendance info via api
        url = event_attendance_list_url(event.id)
        res = self.client.get(url)
        self.assertResOk(res)

        data = res.json()
        self.assertLength(data["results"], 5)
