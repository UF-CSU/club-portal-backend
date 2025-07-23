from clubs.services import ClubService
from clubs.tests.utils import create_test_club
from core.abstracts.tests import PrivateApiTestsBase
from users.tests.utils import create_test_user


class ApiClubViewerTests(PrivateApiTestsBase):
    """
    Test club viewer access to api.

    Most of these tests will probably overlap with the checks
    in the admin tests that ensure admins can only do ops on their
    own clubs, but are repeated here for clarity and in case the
    implementation drifts over time.
    """

    def create_authenticated_user(self):
        self.club = create_test_club()
        self.service = ClubService(self.club)

        user = create_test_user()
        self.service.add_member(user, roles=["Member"])
        return super().create_authenticated_user()

    def test_unable_edit_club(self):
        """Viewers should not be able to edit clubs."""

        self.assertNotImplemented()

    def test_unable_edit_events(self):
        """Viewers should not be able to edit events."""

        self.assertNotImplemented()

    def test_unable_delete_events(self):
        """Viewers should not be able to delete events."""

        self.assertNotImplemented()

    def test_unable_add_events(self):
        """Viewers should not be able to add events or recurring events."""

        self.assertNotImplemented()
