from time import time

from core.abstracts.tests import PublicApiTestsBase
from django.core.cache import cache
from utils.cache import check_cache

from clubs.cache import DETAIL_CLUB_PREVIEW_PREFIX, LIST_CLUB_PREVIEW_PREFIX
from clubs.serializers import ClubPreviewSerializer
from clubs.tests.utils import (
    CLUBS_PREVIEW_LIST_URL,
    club_preview_detail_url,
    create_test_club,
    create_test_club_tag,
    create_test_clubs,
)


class ClubPreviewCacheTests(PublicApiTestsBase):
    def setUp(self):
        cache.clear()
        return super().setUp()

    def tearDown(self):
        cache.clear()
        return super().tearDown()

    def test_list_club_preview_cache(self):
        """For the list endpoint of club previews"""
        url = CLUBS_PREVIEW_LIST_URL

        cached_previews_no_csu = check_cache(
            LIST_CLUB_PREVIEW_PREFIX,
            is_csu_partner=False,
            limit=None,
            offset=None,
        )
        cached_previews_csu = check_cache(
            LIST_CLUB_PREVIEW_PREFIX,
            is_csu_partner=True,
            limit=None,
            offset=None,
        )
        self.assertIsNone(cached_previews_csu)
        self.assertIsNone(cached_previews_no_csu)

        test_clubs = create_test_clubs(count=3)
        start_no_cache = time()
        res = self.client.get(url)
        end_no_cache = time()
        self.assertEqual(len(res.json()["results"]), 3)

        self.assertCountEqual(
            check_cache(
                LIST_CLUB_PREVIEW_PREFIX,
                is_csu_partner=False,
                limit=None,
                offset=None,
            ),
            res.json()["results"],
        )

        start_cache = time()
        res = self.client.get(url)
        end_cache = time()

        print(
            f"""Time No Cache: {end_no_cache - start_no_cache}\nTime Cached: {end_cache - start_cache}"""
        )

        create_test_club()
        res = self.client.get(url)
        self.assertCountEqual(
            res.json()["results"],
            check_cache(
                LIST_CLUB_PREVIEW_PREFIX,
                is_csu_partner=False,
                limit=None,
                offset=None,
            ),
        )

        create_test_club_tag([])
        self.assertCountEqual(
            res.json()["results"],
            check_cache(
                LIST_CLUB_PREVIEW_PREFIX,
                is_csu_partner=False,
                limit=None,
                offset=None,
            ),
        )

        create_test_club_tag(test_clubs)
        res = self.client.get(url)
        self.assertCountEqual(
            res.json()["results"],
            check_cache(
                LIST_CLUB_PREVIEW_PREFIX,
                is_csu_partner=False,
                limit=None,
                offset=None,
            ),
        )

    def test_detail_club_preview_cache(self):
        """For the detail endpoint of club previews"""
        test_club = create_test_club()
        test_club_preview = ClubPreviewSerializer(test_club).data
        cached_preview = check_cache(DETAIL_CLUB_PREVIEW_PREFIX, club_id=test_club.pk)
        self.assertEqual(test_club_preview, cached_preview)

        cache.clear()

        url = club_preview_detail_url(test_club.pk)

        start_no_cache = time()
        res = self.client.get(url)
        end_no_cache = time()
        self.assertEqual(test_club_preview, res.json()["results"])

        cached_preview = check_cache(DETAIL_CLUB_PREVIEW_PREFIX, club_id=test_club.pk)
        self.assertEqual(cached_preview, res.json()["results"])

        start_cache = time()
        res = self.client.get(url)
        end_cache = time()

        print(
            f"""Time No Cache: {end_no_cache - start_no_cache}\nTime Cached: {end_cache - start_cache}"""
        )

        create_test_club_tag([])
        self.assertEqual(
            res.json()["results"],
            check_cache(DETAIL_CLUB_PREVIEW_PREFIX, club_id=test_club.pk),
        )

        create_test_club_tag([test_club])
        res = self.client.get(url)
        self.assertEqual(
            res.json()["results"],
            check_cache(DETAIL_CLUB_PREVIEW_PREFIX, club_id=test_club.pk),
        )
