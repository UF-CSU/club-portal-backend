"""
Event views for static pages, and non-API routes.
"""

import json
import re

from django.contrib.auth.decorators import login_required
from django.http import FileResponse, HttpRequest, JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.utils.timezone import now
from django.views import View

from clubs.models import Club
from events.models import Event, EventCancellation
from events.services import EventService


class RecordAttendanceView(View):
    """Records a club member attended an event."""

    # This is a separate class to enable restricting to only POST
    http_method_names = ['post']

    def post(self, request: HttpRequest, id: int):
        event = get_object_or_404(Event, id=id)

        try:
            EventService(event).record_event_attendance(request.user, json.loads(request.body))
            return redirect("events:attendance_done", id=event.id)
        except json.JSONDecodeError:
            return JsonResponse({"error": "Body is not JSON"}, status=400)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)


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


@login_required()
def cancel_event(request: HttpRequest, event_id: int):
    """Cancels an event with an optional reason."""
    event = get_object_or_404(Event, id=event_id)

    if hasattr(event, "cancellation"):
        return JsonResponse({"error": "This event is already cancelled."}, status=400)

    reason = request.POST.get("reason", "")

    EventCancellation.objects.create(
        event=event, reason=reason, cancelled_by=request.user, cancelled_at=now()
    )
