from typing import Optional

from lib.celery import debounced_task

from clubs.cache import (
    delete_repopulate_preview_detail_cache,
    delete_repopulate_preview_list_cache,
)
from clubs.models import Club


@debounced_task(delay_sec=1)
def regenerate_club_preview_cache_task(club_ids: Optional[list[int]] = None):
    """Delete and recreate club preview cache in a separate Celery worker."""

    # Regenerate list cache
    delete_repopulate_preview_list_cache()

    if club_ids:
        clubs = Club.objects.filter(id__in=club_ids)
    else:
        clubs = Club.objects.all()

    # Regenerate detail cache
    delete_repopulate_preview_detail_cache(clubs)
