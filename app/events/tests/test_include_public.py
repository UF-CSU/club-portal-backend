"""
Test to reproduce the include_public bug.
"""

from clubs.tests.utils import create_test_club
from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient
from users.tests.utils import create_test_user

from events.tests.utils import create_test_event, event_list_url

User = get_user_model()


class IncludePublicBugTest(TestCase):
    """Test that include_public only returns public events from non-followed clubs."""

    def setUp(self):
        # Create two users with different club memberships
        self.user1 = create_test_user(username="user1", email="user1@test.com")
        self.user2 = create_test_user(username="user2", email="user2@test.com")

        # Create two clubs
        self.club1 = create_test_club(name="Club 1")
        self.club2 = create_test_club(name="Club 2")

        # user1 is a member of club1 only
        self.club1.memberships.create(user=self.user1)

        # user2 is a member of club2 only
        self.club2.memberships.create(user=self.user2)

        # Create events for club1 (user1's club)
        self.club1_public_event = create_test_event(
            name="Club 1 Public Event", host=self.club1, is_public=True, is_draft=False
        )
        self.club1_private_event = create_test_event(
            name="Club 1 Private Event",
            host=self.club1,
            is_public=False,
            is_draft=False,
        )

        # Create events for club2 (user1 does NOT follow club2)
        self.club2_public_event = create_test_event(
            name="Club 2 Public Event", host=self.club2, is_public=True, is_draft=False
        )
        self.club2_private_event = create_test_event(
            name="Club 2 Private Event",
            host=self.club2,
            is_public=False,
            is_draft=False,
        )

    def test_include_public_should_not_return_private_events_from_non_followed_clubs(
        self,
    ):
        """
        When include_public=True, should return:
        - All events (public and private) from followed clubs
        - ONLY public events from non-followed clubs

        Should NOT return:
        - Private events from non-followed clubs
        """

        # Use APIClient to test the actual endpoint
        client = APIClient()
        client.force_authenticate(user=self.user1)

        # Test with include_public=True
        url = event_list_url()
        res = client.get(url, {"include_public": "true"})

        self.assertEqual(res.status_code, 200)
        event_ids = [e["id"] for e in res.data["results"]]

        # Should include club1 events (user1's club) - both public and private
        self.assertIn(
            self.club1_public_event.id,
            event_ids,
            "Should include public event from followed club",
        )
        self.assertIn(
            self.club1_private_event.id,
            event_ids,
            "Should include private event from followed club",
        )

        # Should include club2 public event (include_public=True)
        self.assertIn(
            self.club2_public_event.id,
            event_ids,
            "Should include public event from non-followed club",
        )

        # Should NOT include club2 private event
        self.assertNotIn(
            self.club2_private_event.id,
            event_ids,
            "Should NOT include private event from non-followed club",
        )
