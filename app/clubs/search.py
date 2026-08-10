"""
Club search.
"""

from enum import StrEnum

from django_elasticsearch_dsl.search import Search

from .documents import ClubDocument


class ClubSortBy(StrEnum):
    RELEVANCE = "relevance"
    FOLLOWERS_DESC = "followers_desc"
    FOLLOWERS_ASC = "followers_asc"
    NAME_DESC = "name_desc"
    NAME_ASC = "name_asc"
    FOUNDING_YEAR_DESC = "founding_year_desc"
    FOUNDING_YEAR_ASC = "founding_year_asc"


class ClubSearchService:
    """Service class for handling club searches with various options"""

    SORT_OPTIONS = {
        ClubSortBy.RELEVANCE: {"_score": {"order": "desc"}},
        ClubSortBy.FOLLOWERS_DESC: {
            "instagram_followers": {"order": "desc", "missing": "_last"}
        },
        ClubSortBy.FOLLOWERS_ASC: {
            "instagram_followers": {"order": "asc", "missing": "_last"}
        },
        ClubSortBy.NAME_DESC: {"name.raw": {"order": "desc"}},
        ClubSortBy.NAME_ASC: {"name.raw": {"order": "asc"}},
        ClubSortBy.FOUNDING_YEAR_DESC: {"founding_year": {"order": "desc"}},
        ClubSortBy.FOUNDING_YEAR_ASC: {"founding_year": {"order": "asc"}},
    }

    def __init__(self):
        self.document = ClubDocument

    def search(
        self,
        name: str | None = None,
        tags: list[int] | None = None,
        sort: ClubSortBy | None = None,
        limit: int = 20,
        offset: int = 0,
    ):
        """
        Args:
            name: Name search term for fuzzy match
            tags: Filter by tag ids (exact match)
            sort: Sort option (ClubSortBy)
            limit: Maximum number of results to return (default: 20)
            offset: Offset for results (default: 0)

        Returns:
            Dict with result ids, total count, and pagination info
        """

        # Build the filtered search
        search = self._apply_filters_and_search(
            self.document.search(),
            name=name,
            tags=tags,
        )

        # Apply sorting
        effective_sort = sort
        if effective_sort is None:
            # Sort by relevance if name is provided, otherwise sort by followers
            if name:
                effective_sort = ClubSortBy.RELEVANCE
            else:
                effective_sort = ClubSortBy.FOLLOWERS_DESC
        search = self._apply_sorting(search, effective_sort)

        # Calculate pagination offsets
        start = offset
        end = offset + limit

        # Apply pagination
        search = search[start:end]

        # Only return ids
        search = search.source(fields=["id"])

        # Execute the search
        response = search.execute()

        # Return structured results
        return {
            "ids": [hit.id for hit in response],
            "total": response.hits.total.value,
        }

    def _apply_sorting(self, search: Search, sort: ClubSortBy):
        """Apply sorting based on the sort parameter"""

        sort_field = self.SORT_OPTIONS[sort]
        sort_field_with_tiebreaker = [
            sort_field,
            {"id": {"order": "asc"}},
        ]
        return search.sort(*sort_field_with_tiebreaker)

    def _apply_filters_and_search(
        self,
        search: Search,
        name: str | None = None,
        tags: list[int] | None = None,
    ):
        """Apply the shared query and filters used by plain and faceted search."""

        if name:
            search = search.query(
                "bool",
                should=[
                    # Exact/normal name match
                    {
                        "match": {
                            "name": {
                                "query": name,
                                "boost": 8,
                            }
                        }
                    },
                    # Prefix matching
                    {
                        "match_phrase_prefix": {
                            "name": {
                                "query": name,
                                "boost": 4,
                            }
                        }
                    },
                    # Typo tolerance
                    {
                        "match": {
                            "name": {
                                "query": name,
                                "fuzziness": "AUTO",
                                "prefix_length": 1,
                                "boost": 2,
                            }
                        }
                    },
                ],
                minimum_should_match=1,
            )

        if tags:
            search = search.query(
                "bool",
                must=[
                    {
                        "nested": {
                            "path": "tags",
                            "query": {
                                "term": {
                                    "tags.id": tag_id,
                                }
                            },
                        }
                    }
                    for tag_id in tags
                ],
            )

        return search
