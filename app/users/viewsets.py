"""
Views for the user API.
"""

from django.urls import reverse_lazy
from rest_framework import authentication, generics, mixins
from rest_framework.authtoken.models import Token
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.response import Response
from rest_framework.settings import api_settings

from core.abstracts.viewsets import ModelViewSetBase, ViewSetBase
from users.serializers import OauthDirectorySerializer, UserSerializer


class CreateUserView(generics.CreateAPIView):
    """Create a new user in the system."""

    serializer_class = UserSerializer


class AuthTokenView(
    ObtainAuthToken,
    mixins.RetrieveModelMixin,
    ViewSetBase,
):
    """Create a new auth token for user."""

    renderer_classes = api_settings.DEFAULT_RENDERER_CLASSES
    authentication_classes = [
        authentication.TokenAuthentication,
        authentication.SessionAuthentication,
    ]

    def retrieve(self, request, *args, **kwargs):
        token, _ = Token.objects.get_or_create(user=request.user)
        return Response({"token": token.key})


class ManageUserView(generics.RetrieveUpdateAPIView):
    """Manage the authenticated user."""

    serializer_class = UserSerializer
    authentication_classes = ModelViewSetBase.authentication_classes
    permission_classes = ModelViewSetBase.permission_classes

    def get_object(self):
        """Retrieve and return the authenticated user."""
        return self.request.user


class OauthDirectoryView(generics.RetrieveAPIView):
    """
    List available api routes to use with OAuth.

    To use oauth, submit a post request to the given route,
    include the fields: provider, callback_url, and process.
    """

    serializer_class = OauthDirectorySerializer

    def get_object(self):
        """List available oauth providers, all will have the same url."""
        return {
            "google": reverse_lazy("headless:app:socialaccount:redirect_to_provider")
        }
