from asyncio import iscoroutinefunction
from inspect import markcoroutinefunction

from django.http import HttpRequest, HttpResponse


class BaseMiddleware:
    """Base fields for middleware."""

    async_capable = True
    sync_capable = False

    def __init__(self, get_response) -> None:
        """One-time configuration and initialization."""

        self.get_response = get_response

        # Allow other middleware to see this as async
        if iscoroutinefunction(self.get_response):
            markcoroutinefunction(self)

    async def __call__(self, request: HttpRequest):
        """Converts request to response."""

        await self.on_request(request)
        response = await self.get_response(request)
        await self.on_response(response)

        return response

    async def on_request(self, request: HttpRequest, *args, **kwargs):
        """
        Code to be executed for each request before
        the view (and later middleware) are called.
        """

        return

    async def on_response(self, response: HttpResponse, *args, **kwargs):
        """
        Code to be executed for each request/response after
        the view is called.
        """

        return
