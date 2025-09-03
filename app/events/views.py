"""
Event views for static pages, and non-API routes.
"""

import re

from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.http import FileResponse, HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404
from django.utils.timezone import now

from clubs.models import Club
from events.models import Event, EventCancellation
from events.services import EventService

User = get_user_model()


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


def download_user_calendar(request: HttpRequest, calendar_token: str):
    """Download user calendar using secure token // uses webcal://"""
    try:
        user = User.objects.get(calendar_token=calendar_token)
    except User.DoesNotExist:
        return HttpResponse("Invalid calendar token", status=404)
    
    file = EventService.get_user_calendar(user)
    
    user_name = user.name if hasattr(user, 'name') and user.name else user.username
    filename = re.sub(r"\s+", "_", f"{user_name}_calendar")
    
    
    response = HttpResponse(file.read(), content_type='text/calendar; charset=utf-8')
    response['Content-Disposition'] = f'inline; filename="{filename}.ics"'
    
    
    response['Cache-Control'] = 'public, max-age=900'  
    response['ETag'] = f'"{user.calendar_token}-{user.date_modified.timestamp()}"'
    response['Last-Modified'] = user.date_modified.strftime('%a, %d %b %Y %H:%M:%S GMT')
    
    
    response['X-WR-CALNAME'] = f"{user_name}'s Events"
    response['X-WR-CALDESC'] = f"Events from clubs that {user_name} is a member of"
    response['X-Robots-Tag'] = 'noindex'  
    
    return response


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
