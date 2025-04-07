from abc import ABC

from django.http import HttpRequest, HttpResponse


class BaseMiddleware(ABC):
    """Base fields for middleware."""

    def __init__(self, get_response: callable) -> None:
        """One-time configuration and initialization."""

        self.get_response = get_response

    def __call__(self, request: HttpRequest):
        """Converts request to response."""

        self.on_request(request)
        response = self.get_response(request)
        self.on_response(response)

        return response

    def on_request(self, request: HttpRequest, *args, **kwargs):
        """
        Code to be executed for each request before
        the view (and later middleware) are called.
        """

    def on_response(self, response: HttpResponse, *args, **kwargs):
        """
        Code to be executed for each request/response after
        the view is called.
        """
