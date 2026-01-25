# import time

# from django.core.cache import cache

# from clubs.tests.utils import create_test_club
# from core.abstracts.tests import PublicApiTestsBase
# from events.serializers import EventSerializer
# from events.tests.utils import EVENT_LIST_URL, create_test_event

# from ..utils import check_event_cache, generate_event_hash


# class EventCacheTests(PublicApiTestsBase):
#     """Event cache tests for accurate invalidation and key setting"""

#     def setUp(self):
#         cache.clear()
#         return super().setUp()

#     def test_public_retrieve_event_cache(self):
#         """Test retrieving specific events from event cache"""
#         pass

#     def test_public_list_event_cache(self):
#         """Test listing events from event cache"""

#         url = EVENT_LIST_URL
#         club_initial = create_test_club()

#         cached_event_list: list = cache.get(generate_event_hash(club_initial.pk, False))
#         self.assertEqual(
#             None,
#             (
#                 cached_event_list
#                 if not cached_event_list
#                 else EventSerializer(cached_event_list, many=True).data
#             ),
#         )

#         create_test_event(club_initial)
#         create_test_event(club_initial)

#         start_time = time.time()
#         res = self.client.get(url)
#         end_time = time.time()

#         self.assertResOk(res)
#         data = res.json()
#         self.assertEqual(len(data), 2)

#         start_time_cache = time.time()
#         res = self.client.get(url)
#         end_time_cache = time.time()

#         cached_event_list = check_event_cache(club_initial.pk, False)
#         print(len(data))
#         print(len(EventSerializer(cached_event_list, many=True).data))
#         self.assertEqual(data, EventSerializer(cached_event_list, many=True).data)
#         print(
#             f"""Time No Cache: {end_time - start_time}\n
#                   Time Cached: {end_time_cache - start_time_cache}\n"""
#         )

#         test_club_1 = create_test_club()
#         test_club_2 = create_test_club()

#         multi_club_url = url + f"?clubs={test_club_1.pk}&clubs={test_club_2.pk}"
#         res = self.client.get(multi_club_url)

#         self.assertResOk(res)

#         cached_event_list = cache.get(generate_event_hash(test_club_2.pk, False))
#         self.assertEqual(None, EventSerializer(cached_event_list, many=True).data)

#         create_test_event(club_initial)

#         res = self.client.get(url)

#         self.assertResOk(res)
#         self.assertNotEqual(len(data), 3)
