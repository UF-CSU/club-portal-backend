import io
import re

from django.core import exceptions
from django.http import FileResponse, HttpRequest
from django.shortcuts import get_object_or_404, redirect, render
from users.services import UserService

from polls.models import Poll, PollSubmission
from polls.services import PollService


def show_poll_view(request: HttpRequest, poll_id: int):
    """Render template to display a poll as a form."""

    poll = get_object_or_404(Poll, id=poll_id)

    if request.POST:
        data = request.POST

        parsed_data = {
            key: data.getlist(key) if len(data.getlist(key)) > 1 else data.get(key)
            for key in data.keys()
        }

        parsed_data.pop("csrfmiddlewaretoken")

        PollSubmission.objects.create(poll=poll, data=parsed_data, user=request.user)
        return redirect("clubs:polls:poll_success", poll_id=poll_id)

    return render(request, "clubs/polls/poll_form.html", context={"poll": poll})


def poll_success_view(request, poll_id: int):
    """Redirect to this page after poll submission."""

    poll = get_object_or_404(Poll, id=poll_id)

    return render(request, "clubs/polls/poll_success.html", context={"poll": poll})


def download_submissions(request: HttpRequest, poll_id: int):
    """Download poll submissions as a csv."""

    token = request.GET.get("token", None)

    if not token:
        raise exceptions.PermissionDenied()

    user = UserService.get_from_token(token).obj
    poll = get_object_or_404(Poll, id=poll_id)
    if not user.has_perm("polls.view_pollsubmission", poll):
        raise exceptions.PermissionDenied(
            'User does not have "polls.view_pollsubmission" permissions'
        )

    poll = get_object_or_404(Poll, id=poll_id)
    service = PollService(poll)
    filename = f"{re.sub(r'[()]', '', poll.name.lower().replace(' ', '_').replace('/', '_'))}_submissions"
    tzname = request.GET.get("timezone", "UTC")

    df = service.get_submissions_df(tzname)
    buffer = io.BytesIO()
    df.to_csv(
        buffer,
        index=False,
        compression={
            "method": "zip",
            "archive_name": filename + ".csv",
        },
    )
    buffer.seek(0)

    return FileResponse(
        buffer,
        as_attachment=True,
        filename=filename + ".zip",
        content_type="application/x-zip-compressed",
    )
