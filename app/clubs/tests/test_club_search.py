from unittest.mock import MagicMock, patch

from clubs.models import ClubTag
from clubs.search import ClubSearchService, ClubSortBy
from clubs.serializers import ClubPreviewSearchParamSerializer
from clubs.tests.utils import CLUBS_PREVIEW_SEARCH_URL, create_test_clubs
from core.abstracts.tests import PublicApiTestsBase, TestsBase
from django.test import TestCase


class ClubPreviewSearchParamSerializerTests(TestsBase):
    def test_defaults(self):
        serializer = ClubPreviewSearchParamSerializer(data={})

        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertEqual(serializer.validated_data["limit"], 100)
        self.assertEqual(serializer.validated_data["offset"], 0)
        self.assertIsNone(serializer.validated_data["name"])
        self.assertEqual(serializer.validated_data["tags"], [])
        self.assertIsNone(serializer.validated_data["sort"])

    def test_valid_limit(self):
        for limit in [1, 10, 100, 1000]:
            serializer = ClubPreviewSearchParamSerializer(
                data={"limit": limit}
            )

            self.assertTrue(serializer.is_valid(), serializer.errors)
            self.assertEqual(serializer.validated_data["limit"], limit)

    def test_invalid_limit(self):
        for limit in [0, -1, -100]:
            serializer = ClubPreviewSearchParamSerializer(
                data={"limit": limit}
            )

            self.assertFalse(serializer.is_valid())
            self.assertIn("limit", serializer.errors)

    def test_valid_offset(self):
        for offset in [0, 1, 10, 100]:
            serializer = ClubPreviewSearchParamSerializer(
                data={"offset": offset}
            )

            self.assertTrue(serializer.is_valid(), serializer.errors)
            self.assertEqual(serializer.validated_data["offset"], offset)

    def test_invalid_offset(self):
        for offset in [-1, -10]:
            serializer = ClubPreviewSearchParamSerializer(
                data={"offset": offset}
            )

            self.assertFalse(serializer.is_valid())
            self.assertIn("offset", serializer.errors)

    def test_valid_name(self):
        for name in ["Bal", "Chess Club", "", "123"]:
            serializer = ClubPreviewSearchParamSerializer(
                data={"name": name}
            )

            self.assertTrue(serializer.is_valid(), serializer.errors)
            self.assertEqual(serializer.validated_data["name"], name)

    def test_null_name(self):
        serializer = ClubPreviewSearchParamSerializer(
            data={"name": None}
        )

        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertIsNone(serializer.validated_data["name"])

    def test_valid_tags(self):
        tag1 = ClubTag.objects.create(name="Academic")
        tag2 = ClubTag.objects.create(name="Sports")

        serializer = ClubPreviewSearchParamSerializer(
            data={"tags": [tag1.pk, tag2.pk]}
        )

        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertEqual(
            serializer.validated_data["tags"],
            [tag1, tag2],
        )

    def test_empty_tags(self):
        serializer = ClubPreviewSearchParamSerializer(
            data={"tags": []}
        )

        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertEqual(serializer.validated_data["tags"], [])

    def test_invalid_tag_id(self):
        serializer = ClubPreviewSearchParamSerializer(
            data={"tags": [999999]}
        )

        self.assertFalse(serializer.is_valid())
        self.assertIn("tags", serializer.errors)

    def test_invalid_tag_id_string(self):
        serializer = ClubPreviewSearchParamSerializer(
            data={"tags": ["not-an-id"]}
        )

        self.assertFalse(serializer.is_valid())
        self.assertIn("tags", serializer.errors)

    def test_tags_must_be_list(self):
        serializer = ClubPreviewSearchParamSerializer(
            data={"tags": 1}
        )

        self.assertFalse(serializer.is_valid())
        self.assertIn("tags", serializer.errors)

    def test_valid_sort_values(self):
        for sort in ClubSortBy:
            serializer = ClubPreviewSearchParamSerializer(
                data={"sort": sort.value}
            )

            self.assertTrue(serializer.is_valid(), serializer.errors)
            self.assertEqual(
                serializer.validated_data["sort"],
                sort.value,
            )

    def test_invalid_sort(self):
        serializer = ClubPreviewSearchParamSerializer(
            data={"sort": "invalid_sort"}
        )

        self.assertFalse(serializer.is_valid())
        self.assertIn("sort", serializer.errors)

    def test_null_sort(self):
        serializer = ClubPreviewSearchParamSerializer(
            data={"sort": None}
        )

        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertIsNone(serializer.validated_data["sort"])


class ClubSearchServiceTests(TestCase):
    def setUp(self):
        self.service = ClubSearchService()

    def test_name_search(self):
        search = self.service._apply_filters_and_search(
            self.service.document.search(),
            name="Bal",
        )

        query = search.to_dict()

        self.assertEqual(
            query["query"]["bool"]["minimum_should_match"],
            1,
        )

        should = query["query"]["bool"]["should"]

        self.assertEqual(len(should), 3)

        # Normal name match
        self.assertEqual(
            should[0]["match"]["name"]["query"],
            "Bal",
        )
        self.assertEqual(
            should[0]["match"]["name"]["boost"],
            8,
        )

        # Prefix match
        self.assertEqual(
            should[1]["match_phrase_prefix"]["name"]["query"],
            "Bal",
        )
        self.assertEqual(
            should[1]["match_phrase_prefix"]["name"]["boost"],
            4,
        )

        # Fuzzy match
        self.assertEqual(
            should[2]["match"]["name"]["query"],
            "Bal",
        )
        self.assertEqual(
            should[2]["match"]["name"]["fuzziness"],
            "AUTO",
        )
        self.assertEqual(
            should[2]["match"]["name"]["prefix_length"],
            1,
        )
        self.assertEqual(
            should[2]["match"]["name"]["boost"],
            2,
        )

    def test_tag_filter(self):
        search = self.service._apply_filters_and_search(
            self.service.document.search(),
            tags=[1, 2],
        )

        query = search.to_dict()

        must = query["query"]["bool"]["must"]

        self.assertEqual(len(must), 2)

        self.assertEqual(
            must[0]["nested"]["path"],
            "tags",
        )
        self.assertEqual(
            must[0]["nested"]["query"]["term"]["tags.id"],
            1,
        )

        self.assertEqual(
            must[1]["nested"]["path"],
            "tags",
        )
        self.assertEqual(
            must[1]["nested"]["query"]["term"]["tags.id"],
            2,
        )

    def test_no_filters(self):
        search = self.service._apply_filters_and_search(
            self.service.document.search(),
        )

        self.assertEqual(
            search.to_dict(),
            {},
        )

    @patch.object(ClubSearchService, "_apply_sorting")
    def test_name_defaults_to_relevance(self, mock_sort):
        mock_sort.side_effect = lambda search, _: search

        response = MagicMock()
        response.__iter__.return_value = []
        response.hits.total.value = 0

        mock_search = MagicMock()
        mock_search.__getitem__.return_value = mock_search
        mock_search.source.return_value = mock_search
        mock_search.execute.return_value = response

        with patch.object(
            self.service.document,
            "search",
            return_value=mock_search,
        ):
            self.service.search(name="Bal")

        _, sort = mock_sort.call_args.args

        self.assertEqual(
            sort,
            ClubSortBy.RELEVANCE,
        )

    @patch.object(ClubSearchService, "_apply_sorting")
    def test_no_name_defaults_to_followers_desc(self, mock_sort):
        mock_sort.side_effect = lambda search, _: search

        response = MagicMock()
        response.__iter__.return_value = []
        response.hits.total.value = 0

        mock_search = MagicMock()
        mock_search.__getitem__.return_value = mock_search
        mock_search.source.return_value = mock_search
        mock_search.execute.return_value = response

        with patch.object(
            self.service.document,
            "search",
            return_value=mock_search,
        ):
            self.service.search()

        _, sort = mock_sort.call_args.args

        self.assertEqual(
            sort,
            ClubSortBy.FOLLOWERS_DESC,
        )

    def test_sort_options(self):
        for sort, expected in self.service.SORT_OPTIONS.items():
            search = self.service.document.search()

            result = self.service._apply_sorting(search, sort)

            self.assertEqual(result.to_dict()["sort"], [
                expected,
                {"id": {"order": "asc"}},
            ])

    @patch.object(ClubSearchService, "_apply_sorting")
    def test_pagination(self, mock_sort):
        mock_sort.side_effect = lambda search, _: search

        response = MagicMock()
        response.__iter__.return_value = []
        response.hits.total.value = 0

        mock_search = MagicMock()
        mock_search.__getitem__.return_value = mock_search
        mock_search.source.return_value = mock_search
        mock_search.execute.return_value = response

        with patch.object(
            self.service.document,
            "search",
            return_value=mock_search,
        ):
            self.service.search(
                limit=10,
                offset=20,
            )

        mock_search.__getitem__.assert_called_once_with(slice(20, 30))

    @patch.object(ClubSearchService, "_apply_sorting")
    def test_returns_ids_and_total(self, mock_sort):
        mock_sort.side_effect = lambda search, _: search

        hit1 = MagicMock()
        hit1.id = 123

        hit2 = MagicMock()
        hit2.id = 456

        response = MagicMock()
        response.__iter__.return_value = [hit1, hit2]
        response.hits.total.value = 25

        mock_search = MagicMock()
        mock_search.__getitem__.return_value = mock_search
        mock_search.source.return_value = mock_search
        mock_search.execute.return_value = response

        with patch.object(
            self.service.document,
            "search",
            return_value=mock_search,
        ):
            result = self.service.search(
                limit=2,
                offset=10,
            )

        self.assertEqual(
            result,
            {
                "ids": [123, 456],
                "total": 25,
            },
        )


class ClubPreviewSearchTests(PublicApiTestsBase):
    @patch("clubs.viewsets.ClubSearchService.search")
    def test_search_preserves_service_order(self, mock_search):
        clubs = create_test_clubs(count=3)

        # Deliberately return them in a different order than the DB.
        ordered_ids = [
            clubs[2].id,
            clubs[0].id,
            clubs[1].id,
        ]

        mock_search.return_value = {
            "ids": ordered_ids,
            "total": 3,
        }

        response = self.client.get(CLUBS_PREVIEW_SEARCH_URL)

        self.assertResOk(response)

        result_ids = [
            club["id"]
            for club in response.json()["results"]
        ]

        self.assertEqual(result_ids, ordered_ids)