from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase


class EventStatusMigrationTests(TransactionTestCase):
    """Verify that the workflow migration preserves existing publication state."""

    migrate_from = [("events", "0030_recurringevent_template")]
    migrate_to = [("events", "0031_event_status")]

    def setUp(self):
        super().setUp()
        self.executor = MigrationExecutor(connection)
        self.executor.migrate(self.migrate_from)
        old_apps = self.executor.loader.project_state(self.migrate_from).apps
        Event = old_apps.get_model("events", "Event")

        self.draft = Event.objects.create(name="Draft", is_draft=True)
        self.published = Event.objects.create(name="Published", is_draft=False)

    def tearDown(self):
        executor = MigrationExecutor(connection)
        executor.migrate(executor.loader.graph.leaf_nodes())
        super().tearDown()

    def test_existing_drafts_and_published_events_keep_their_state(self):
        self.executor = MigrationExecutor(connection)
        self.executor.migrate(self.migrate_to)
        apps = self.executor.loader.project_state(self.migrate_to).apps
        Event = apps.get_model("events", "Event")

        self.assertEqual(Event.objects.get(pk=self.draft.pk).status, "DRAFT")
        self.assertEqual(Event.objects.get(pk=self.published.pk).status, "PUBLISHED")
