from clubs.models import Club
from clubs.tests.utils import create_test_clubs
from django.utils import timezone
from lib.faker import fake
from querycsv.tests.utils import UploadCsvTestsBase

from events.models import Event, EventTag
from events.serializers import EventCsvSerializer


class EventCsvTests(UploadCsvTestsBase):
    """Test how events are handled in csvs."""

    model_class = Event
    serializer_class = EventCsvSerializer

    def test_create_events_from_csv(self):
        """Uploading a csv should create events and assign to clubs."""

        clubs = create_test_clubs(count=5).order_by("-id")

        payload = [
            {
                "name": fake.title(),
                "description": fake.paragraph(),
                "location": fake.address(),
                "start_at": timezone.datetime(
                    year=2025, month=1, day=1, hour=18, minute=0
                ),
                "end_at": timezone.datetime(
                    year=2025, month=1, day=1, hour=20, minute=0
                ),
                "tags": "Tag 1, Tag 2",
                "clubs": f"{clubs[0].name}, {clubs[1].name}",
            },
            {
                "name": fake.title(),
                "description": fake.paragraph(),
                "location": fake.address(),
                "start_at": timezone.datetime(
                    year=2025, month=1, day=2, hour=18, minute=0
                ),
                "end_at": timezone.datetime(
                    year=2025, month=1, day=2, hour=20, minute=0
                ),
                "tags": "Tag 3",
                "clubs": clubs[2].name,
            },
            {
                "name": fake.title(),
                "description": fake.paragraph(),
                "location": fake.address(),
                "start_at": timezone.datetime(
                    year=2025, month=1, day=3, hour=18, minute=0
                ),
                "end_at": timezone.datetime(
                    year=2025, month=1, day=3, hour=20, minute=0
                ),
                "tags": "Tag 3",
                "clubs": ",".join(club.name for club in clubs),
            },
        ]

        self.assertUploadPayload(payload)
        self.assertEqual(self.repo.count(), len(payload))
        self.assertEqual(Club.objects.count(), 5)
        self.assertEqual(EventTag.objects.count(), 3)
