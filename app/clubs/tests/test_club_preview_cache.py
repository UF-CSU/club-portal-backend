import logging
from time import time

from core.abstracts.tests import PublicApiTestsBase
from django.core.cache import cache
from django.urls import reverse
from utils.cache import check_cache

from clubs.cache import DETAIL_CLUB_PREVIEW_PREFIX, LIST_CLUB_PREVIEW_PREFIX
from clubs.serializers import ClubPreviewSerializer
from clubs.tests.utils import (
    CLUBS_PREVIEW_LIST_URL,
    club_preview_detail_url,
    create_test_club,
    create_test_clubs,
    create_test_clubtag,
)

logger = logging.getLogger(__name__)


class ClubPreviewCacheTests(PublicApiTestsBase):
    def setUp(self):
        cache.clear()
        return super().setUp()

    def tearDown(self):
        cache.clear()
        return super().tearDown()

    def test_valid_params_retrieve(self):
        """To ensure params are validated correctly and return the correct error response if not"""
        test_club = create_test_club()
        test_club_preview = ClubPreviewSerializer(test_club).data
        cache.clear()

        retrieve_url = club_preview_detail_url(test_club.pk)

        res = self.client.get(retrieve_url)
        self.assertEqual(test_club_preview, res.json())

        retrieve_url = club_preview_detail_url("imastring")

        res = self.client.get(retrieve_url)
        self.assertResBadRequest(res)

        retrieve_url = club_preview_detail_url(-1)

        res = self.client.get(retrieve_url)
        self.assertResBadRequest(res)

        retrieve_url = club_preview_detail_url(0)

        res = self.client.get(retrieve_url)
        self.assertResBadRequest(res)

        retrieve_url = club_preview_detail_url("NaN")

        res = self.client.get(retrieve_url)
        self.assertResBadRequest(res)

        retrieve_url = club_preview_detail_url(123123)

        res = self.client.get(retrieve_url)
        self.assertResNotFound(res)

    def test_valid_params_list(self):
        """To ensure params are validated correctly and return the correct error response if not"""
        url = CLUBS_PREVIEW_LIST_URL
        cache.clear()

        create_test_clubs(count=3)
        create_test_club(is_csu_partner=True)
        res = self.client.get(url)
        self.assertResOk(res)
        self.assertEqual(len(res.json()["results"]), 4)

        url = reverse(
            "api-clubs:clubpreview-list",
            query={"limit": -1, "offset": -10, "is_csu_partner": "abc"},
        )
        res = self.client.get(url)
        self.assertResBadRequest(res)

        url = reverse(
            "api-clubs:clubpreview-list",
            query={"limit": 1, "offset": "abda", "is_csu_partner": "abc"},
        )
        res = self.client.get(url)
        self.assertResBadRequest(res)

        url = reverse(
            "api-clubs:clubpreview-list",
            query={"limit": 1, "offset": 1, "is_csu_partner": "-1"},
        )
        res = self.client.get(url)
        self.assertResBadRequest(res)

        url = reverse(
            "api-clubs:clubpreview-list",
            query={"limit": 1, "is_csu_partner": False},
        )
        res = self.client.get(url)
        club1 = res.json()
        self.assertResOk(res)
        self.assertEqual(len(club1["results"]), 1)
        self.assertFalse(club1["results"][0]["is_csu_partner"])

        url = reverse(
            "api-clubs:clubpreview-list",
            query={"limit": 1, "offset": 1, "is_csu_partner": False},
        )
        res = self.client.get(url)
        club2 = res.json()
        self.assertResOk(res)
        self.assertEqual(len(club2["results"]), 1)
        self.assertFalse(club2["results"][0]["is_csu_partner"])
        self.assertNotEqual(club1, club2)

        url = reverse(
            "api-clubs:clubpreview-list",
            query={"limit": 1, "offset": 1, "is_csu_partner": 0},
        )
        res = self.client.get(url)
        club3 = res.json()
        self.assertResOk(res)
        self.assertEqual(len(club3["results"]), 1)
        self.assertFalse(club3["results"][0]["is_csu_partner"])

        url = reverse(
            "api-clubs:clubpreview-list",
            query={"limit": 1, "offset": 1, "is_csu_partner": "faLsE"},
        )
        res = self.client.get(url)
        club4 = res.json()
        self.assertResOk(res)
        self.assertEqual(len(club4["results"]), 1)
        self.assertFalse(club4["results"][0]["is_csu_partner"])

        url = reverse(
            "api-clubs:clubpreview-list",
            query={"is_csu_partner": "tRuE", "limit": 1},
        )
        res = self.client.get(url)
        clubs = res.json()
        self.assertResOk(res)
        self.assertEqual(len(clubs["results"]), 1)
        self.assertTrue(clubs["results"][0]["is_csu_partner"])

        url = reverse(
            "api-clubs:clubpreview-list",
            query={"is_csu_partner": True, "limit": 1},
        )
        res = self.client.get(url)
        clubs = res.json()
        self.assertResOk(res)
        self.assertEqual(len(clubs["results"]), 1)
        self.assertTrue(clubs["results"][0]["is_csu_partner"])

        url = reverse(
            "api-clubs:clubpreview-list",
            query={"is_csu_partner": 1, "limit": 1},
        )
        res = self.client.get(url)
        clubs = res.json()
        self.assertResOk(res)
        self.assertEqual(len(clubs["results"]), 1)
        self.assertTrue(clubs["results"][0]["is_csu_partner"])

        url = reverse(
            "api-clubs:clubpreview-list",
            query={"is_csu_partner": False},
        )
        res = self.client.get(url)
        clubs = res.json()
        self.assertResOk(res)
        self.assertEqual(len(clubs["results"]), 3)
        for c in clubs["results"]:
            self.assertFalse(c["is_csu_partner"])

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
                is_csu_partner=None,
                limit=None,
                offset=None,
            )["results"],
            res.json()["results"],
        )

        start_cache = time()
        res = self.client.get(url)
        end_cache = time()

        logger.debug(
            f"""Time No Cache: {end_no_cache - start_no_cache}\nTime Cached: {end_cache - start_cache}"""
        )

        create_test_club()
        res = self.client.get(url)
        self.assertCountEqual(
            res.json()["results"],
            check_cache(
                LIST_CLUB_PREVIEW_PREFIX,
                is_csu_partner=None,
                limit=None,
                offset=None,
            )["results"],
        )

        create_test_clubtag([])
        self.assertCountEqual(
            res.json()["results"],
            check_cache(
                LIST_CLUB_PREVIEW_PREFIX,
                is_csu_partner=None,
                limit=None,
                offset=None,
            )["results"],
        )

        create_test_clubtag(test_clubs)
        res = self.client.get(url)
        self.assertCountEqual(
            res.json()["results"],
            check_cache(
                LIST_CLUB_PREVIEW_PREFIX,
                is_csu_partner=None,
                limit=None,
                offset=None,
            )["results"],
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
        self.assertEqual(test_club_preview, res.json())

        cached_preview = check_cache(DETAIL_CLUB_PREVIEW_PREFIX, club_id=test_club.pk)
        self.assertEqual(cached_preview, res.json())

        start_cache = time()
        res = self.client.get(url)
        end_cache = time()

        logger.debug(
            f"""Time No Cache: {end_no_cache - start_no_cache}\nTime Cached: {end_cache - start_cache}"""
        )

        create_test_clubtag([])
        self.assertEqual(
            res.json(),
            check_cache(DETAIL_CLUB_PREVIEW_PREFIX, club_id=test_club.pk),
        )

        create_test_clubtag([test_club])
        res = self.client.get(url)
        self.assertEqual(
            res.json(),
            check_cache(DETAIL_CLUB_PREVIEW_PREFIX, club_id=test_club.pk),
        )
