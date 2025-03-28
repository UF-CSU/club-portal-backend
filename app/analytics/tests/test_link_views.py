from analytics.models import Link, QRCode
from clubs.tests.utils import create_test_club
from core.abstracts.tests import ViewTestsBase
from lib.faker import fake


def create_test_link(club=None, **kwargs):
    """Create mock link for testing."""

    payload = {"target_url": fake.url(), "club": club or create_test_club(), **kwargs}

    return Link.objects.create(**payload)


class LinkViewTests(ViewTestsBase):
    """Test link functionality."""

    def test_visit_link(self):
        """Should record link visit."""
        ip1 = fake.ipv4_public()
        ip2 = fake.ipv4_public()
        link = create_test_link()

        # Initial visit
        res = self.client.get(link.tracking_url, REMOTE_ADDR=ip1)
        self.assertRedirects(res, expected_url=link.target_url)

        self.assertEqual(link.visits.count(), 1)
        visit = link.visits.first()
        self.assertEqual(visit.amount, 1)
        self.assertEqual(visit.ipaddress, ip1)

        # Subsequent visit, same ip
        res2 = self.client.get(link.tracking_url, REMOTE_ADDR=ip1)
        self.assertRedirects(res2, expected_url=link.target_url)

        link.refresh_from_db()
        self.assertEqual(link.visits.count(), 1)
        visit.refresh_from_db()
        self.assertEqual(visit.amount, 2)
        self.assertEqual(visit.ipaddress, ip1)

        # Subsequent visit, different ip
        res = self.client.get(link.tracking_url, REMOTE_ADDR=ip2)
        self.assertRedirects(res, expected_url=link.target_url)

        self.assertEqual(link.visits.count(), 2)

    def test_link_qrcode(self):
        """Should create qrcode when specified."""

        link1 = create_test_link(create_qrcode=False)
        self.assertIsNone(link1.qrcode)

        link2 = create_test_link(create_qrcode=True)
        self.assertIsInstance(link2.qrcode, QRCode)
        self.assertIsNotNone(link2.qrcode.image)
        self.assertIsNotNone(link2.qrcode.image.file)
