from django.http import HttpRequest
from django.shortcuts import get_object_or_404, redirect, render

from polls.models import Poll, PollSubmission


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
