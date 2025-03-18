"""
Event views for static pages, and non-API routes.
"""

import re

from django.contrib.auth.decorators import login_required
from django.http import FileResponse, HttpRequest
from django.shortcuts import get_object_or_404, redirect

from clubs.models import Club
from events.models import Event
from events.services import EventService


@login_required()
def record_attendance_view(request: HttpRequest, id: int):
    """Records a club member attended an event."""
    event = get_object_or_404(Event, id=id)
    EventService(event).record_event_attendance(request.user)

    return redirect("events:attendance_done", id=event.id)


def download_event_calendar(request: HttpRequest, event_id: int):
    event = get_object_or_404(Event, id=event_id)
    file = EventService(event).get_event_calendar()

    event_name = re.sub(r"\s+", "_", event.name)
    return FileResponse(file, as_attachment=True, filename=f"{event_name}.ics")


def download_club_calendar(request: HttpRequest, club_id: int):
    club = get_object_or_404(Club, id=club_id)
    file = EventService.get_club_calendar(club)

    club_name = re.sub(r"\s+", "_", club.name)
    return FileResponse(file, as_attachment=True, filename=f"{club_name}.ics")
