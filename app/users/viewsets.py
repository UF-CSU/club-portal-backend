"""
Views for the user API.
"""

from allauth.headless.base.views import APIView
from allauth.headless.socialaccount.forms import RedirectToProviderForm
from allauth.socialaccount.models import SocialAccount
from django.core import exceptions
from django.core.exceptions import BadRequest
from django.http import HttpRequest
from django.shortcuts import redirect
from django.urls import reverse, reverse_lazy
from drf_spectacular.utils import extend_schema
from rest_framework import (
    authentication,
    generics,
    mixins,
    permissions,
    status,
    viewsets,
)
from rest_framework.authtoken.models import Token
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.decorators import action
from rest_framework.exceptions import AuthenticationFailed, ParseError
from rest_framework.response import Response
from rest_framework.settings import api_settings

from core.abstracts.viewsets import ModelViewSetBase, ViewSetBase
from lib.allauth import OauthProviderType
from users.models import User
from users.serializers import (
    CheckEmailVerificationRequestSerializer,
    EmailVerificationRequestSerializer,
    OauthDirectorySerializer,
    SocialProviderSerializer,
    UserSerializer,
)
from users.services import UserService
from utils.urls import prepare_url


class UserViewSet(mixins.RetrieveModelMixin, ViewSetBase):
    """Create a new user in the system."""

    serializer_class = UserSerializer
    queryset = User.objects.all()


class PublicUserViewSet(mixins.CreateModelMixin, ViewSetBase):
    """Create a new user without OAuth authentication."""

    serializer_class = UserSerializer
    queryset = User.objects.all()
    permission_classes = [permissions.AllowAny]


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

    @extend_schema(auth=[{"security": []}, {}])
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)

    def retrieve(self, request, *args, **kwargs):
        if request.user.is_anonymous:
            raise AuthenticationFailed(
                "Unable to retrieve token for unauthenticated user."
            )

        token, _ = Token.objects.get_or_create(user=request.user)
        return Response({"token": token.key})


class ManageUserView(generics.RetrieveUpdateAPIView):
    """Manage the authenticated user."""

    serializer_class = UserSerializer
    authentication_classes = ModelViewSetBase.authentication_classes
    permission_classes = [permissions.IsAuthenticated]

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


class EmailVerificationViewSet(mixins.CreateModelMixin, ViewSetBase):
    """Send and check email verification codes."""

    serializer_class = EmailVerificationRequestSerializer

    def perform_create(self, serializer: serializer_class):
        try:
            UserService(self.request.user).send_verification_code(
                serializer.validated_data.get("email")
            )
        except Exception as e:
            raise ParseError(e, code="verification_error")

        return serializer.data

    @action(
        methods=["POST"],
        detail=False,
        serializer_class=CheckEmailVerificationRequestSerializer,
    )
    def check(self, request: HttpRequest):
        """Allow user to check verification code."""

        serializer = CheckEmailVerificationRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            UserService(self.request.user).check_verification_code(
                email=serializer.validated_data.get("email"),
                code=serializer.validated_data.get("code"),
                raise_exception=True,
            )
        except BadRequest as e:
            raise ParseError(e, code="verification_error")

        return Response({"success": True}, status=status.HTTP_201_CREATED)


class SocialProviderViewSet(mixins.ListModelMixin, ViewSetBase):
    """Display social account providers for a user."""

    serializer_class = SocialProviderSerializer
    queryset = SocialAccount.objects.none()

    def get_queryset(self):
        return SocialAccount.objects.filter(user=self.request.user)


class RedirectToProviderView(viewsets.GenericViewSet):
    """
    Override allauth's redirect logic to authenticate existing users
    with their token as a query param.
    """

    handle_json_input = False

    def post(self, request, *args, **kwargs):
        # Authenticate via token in url query params
        token = request.GET.get("token", None)

        if token:
            user_service = UserService.get_from_token(token)
            user_service.login(request)

        # Continue to provider
        form = RedirectToProviderForm(request.POST)
        if not form.is_valid():
            raise exceptions.BadRequest(form.errors.as_json())

        provider: OauthProviderType = form.cleaned_data["provider"]
        next_url = (
            reverse("api-users:oauth_return")
            + "?next="
            + form.cleaned_data["callback_url"]
        )
        process = form.cleaned_data["process"]
        return provider.redirect(
            request,
            process,
            next_url=next_url,
            headless=True,
        )


class ReturnFromOauthView(APIView):
    """
    Override allauth's logic for redirecting back to client side to provide
    the user's token as a query param. No matter if the token was provided initially,
    the user will be authenticated at this point so it will always have a token.
    """

    def get(self, request, *args, **kwargs):
        user = request.user
        next_url = request.GET.get("next")

        if user.is_anonymous:
            return redirect(
                prepare_url(next_url, {"error": "Error authenticating user with oauth"})
            )

        token, _ = Token.objects.get_or_create(user=user)
        return redirect(prepare_url(next_url, {"token": token.key}))
