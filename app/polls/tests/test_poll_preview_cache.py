import logging
from time import time

from core.abstracts.tests import PublicApiTestsBase
from django.core.cache import cache
from events.tests.utils import create_test_event
from utils.cache import check_cache

from polls.cache import (
    DETAIL_POLL_PREVIEW_PREFIX,
    LIST_POLL_PREVIEW_PREFIX,
)
from polls.serializers import PollPreviewSerializer
from polls.tests.utils import (
    POLL_PREVIEW_LIST_URL,
    create_test_poll,
    pollpreview_detail_url,
)

logger = logging.getLogger(__name__)


class PollPreviewCacheTests(PublicApiTestsBase):
    def setUp(self):
        cache.clear()
        return super().setUp()

    def tearDown(self):
        cache.clear()
        return super().tearDown()

    def test_detail_poll_preview_cache(self):
        """Test for the poll preview cache detail endpoint"""
        test_poll = create_test_poll()
        test_poll_preview = PollPreviewSerializer(test_poll).data
        cached_preview = check_cache(DETAIL_POLL_PREVIEW_PREFIX, poll_id=test_poll.pk)
        self.assertEqual(test_poll_preview, cached_preview)

        cache.clear()

        url = pollpreview_detail_url(test_poll.pk)

        start_no_cache = time()
        res = self.client.get(url)
        end_no_cache = time()
        self.assertEqual(test_poll_preview, res.data)

        cached_preview = check_cache(DETAIL_POLL_PREVIEW_PREFIX, poll_id=test_poll.pk)
        self.assertEqual(cached_preview, res.data)

        start_cache = time()
        res = self.client.get(url)
        end_cache = time()

        logger.debug(
            f"""Time No Cache: {end_no_cache - start_no_cache}\nTime Cached: {end_cache - start_cache}"""
        )

        test_poll.event = create_test_event()
        res = self.client.get(url)
        self.assertEqual(
            res.data, check_cache(DETAIL_POLL_PREVIEW_PREFIX, poll_id=test_poll.pk)
        )

    def test_list_poll_preview_cache(self):
        """Test for the poll preview cache list endpoint"""
        url = POLL_PREVIEW_LIST_URL

        cached_previews = check_cache(LIST_POLL_PREVIEW_PREFIX)
        self.assertIsNone(cached_previews)

        create_test_poll()
        create_test_poll()
        create_test_poll()

        start_no_cache = time()
        res = self.client.get(url)
        end_no_cache = time()
        self.assertEqual(len(res.data), 3)

        cached_previews = check_cache(LIST_POLL_PREVIEW_PREFIX)
        self.assertEqual(cached_previews, res.data)

        start_cache = time()
        res = self.client.get(url)
        end_cache = time()

        logger.debug(
            f"""Time No Cache: {end_no_cache - start_no_cache}\nTime Cached: {end_cache - start_cache}"""
        )

        test_poll = create_test_poll()
        res = self.client.get(url)
        self.assertEqual(res.data, check_cache(LIST_POLL_PREVIEW_PREFIX))

        test_poll.event = create_test_event()
        res = self.client.get(url)
        self.assertEqual(res.data, check_cache(LIST_POLL_PREVIEW_PREFIX))
