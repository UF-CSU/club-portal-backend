from utils.cache import clear_cache, set_cache

from clubs.models import Club
from clubs.serializers import ClubPreviewSerializer

LIST_CLUB_PREVIEW_PREFIX = "club-previews"
DETAIL_CLUB_PREVIEW_PREFIX = "club-preview"


def delete_repopulate_preview_list_cache():
    """Delete preview pairs from previews cache"""
    clear_cache(LIST_CLUB_PREVIEW_PREFIX)
    set_cache(
        ClubPreviewSerializer(Club.objects.filter(is_csu_partner=True).distinct(), many=True).data,
        LIST_CLUB_PREVIEW_PREFIX,
        is_csu_partner=True,
        limit=None,
        offset=None,
    )
    set_cache(
        ClubPreviewSerializer(Club.objects.filter(is_csu_partner=False).distinct(), many=True).data,
        LIST_CLUB_PREVIEW_PREFIX,
        is_csu_partner=False,
        limit=None,
        offset=None,
    )

    # INITIAL CACHE PREVIEW ENDPOINT
    set_cache(
        ClubPreviewSerializer(Club.objects.filter(is_csu_partner=False).distinct(), many=True).data,
        LIST_CLUB_PREVIEW_PREFIX,
        is_csu_partner=False,
        limit=100,
        offset=0,
    )


def delete_repopulate_preview_detail_cache(clubs: list[Club]):
    """Delete modified club keys from previews cache"""
    for club in clubs:
        set_cache(
            ClubPreviewSerializer(Club.objects.find_by_id(club.pk)).data,
            DETAIL_CLUB_PREVIEW_PREFIX,
            club_id=club.pk,
        )
