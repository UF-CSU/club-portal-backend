from time import time

from core.abstracts.tests import PublicApiTestsBase
from django.core.cache import cache

from clubs.cache import check_preview_list_cache
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

    def test_list_club_preview_cache(self):
        """For the list endpoint of club previews"""
        url = CLUBS_PREVIEW_LIST_URL

        cached_previews_no_csu = check_preview_list_cache(False)
        cached_previews_csu = check_preview_list_cache(True)
        self.assertIsNone(cached_previews_csu)
        self.assertIsNone(cached_previews_no_csu)

        test_clubs = create_test_clubs(count=3)
        start_no_cache = time()
        res = self.client.get(url)
        end_no_cache = time()
        self.assertEqual(len(res.data), 3)

        cached_previews_no_csu = check_preview_list_cache(False)
        self.assertEqual(cached_previews_no_csu, res.data)

        start_cache = time()
        res = self.client.get(url)
        end_cache = time()

        print(
            f"""Time No Cache: {end_no_cache- start_no_cache}\nTime Cached: {end_cache - start_cache}"""
        )

        create_test_club()
        res = self.client.get(url)
        self.assertEqual(res.data, check_preview_list_cache(False))

        create_test_club_tag([])
        self.assertEqual(res.data, check_preview_list_cache(False))

        create_test_club_tag(test_clubs)
        res = self.client.get(url)
        self.assertEqual(res.data, check_preview_list_cache(False))

    def test_detail_club_preview_cache(self):
        """For the detail endpoint of club previews"""
        test_club = create_test_club()

        url = club_preview_detail_url(test_club.pk)
