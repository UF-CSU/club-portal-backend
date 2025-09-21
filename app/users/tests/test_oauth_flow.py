from typing import Literal
from unittest.mock import Mock, patch
from urllib.parse import parse_qs, urlparse

import requests
from allauth.socialaccount.providers.oauth2.views import OAuth2Adapter
from django.http import JsonResponse
from django.urls import reverse
from rest_framework import exceptions, status

from core.abstracts.tests import EmailTestsBase, PublicApiTestsBase
from lib.faker import fake
from users.models import EmailVerificationCode, User
from users.tests.utils import (
    CHECK_EMAIL_VERIFICATION_URL,
    SEND_EMAIL_VERIFICATION_URL,
    create_test_user,
)


class PublicGoogleOauthTests(PublicApiTestsBase, EmailTestsBase):
    """Unit tests for oauth using unauthenticated users."""

    @patch.object(requests.Session, "get")
    @patch.object(
        OAuth2Adapter,
        "get_access_token_data",
        return_value={"access_token": "testaccesstoken"},
    )
    def assertDoOauthFlow(
        self,
        mock_get_access_token=None,
        mock_session_get=None,
        return_email="john.doe@example.com",
        return_first_name="John",
        return_last_name="Doe",
        process: Literal["login", "connect"] = "login",
        **kwargs,
    ):
        """Do the oauth flow for a user, and return final token."""

        # Allauth calls Session.get when getting user profile info from google
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.ok = True
        mock_response.json.return_value = {
            "family_name": return_last_name,
            "name": f"{return_first_name} {return_last_name}",
            "picture": fake.image_url(width=200, height=200),
            "email": return_email,
            "given_name": return_first_name,
            "id": "1234567890",
            "verified_email": True,
            **kwargs,
        }
        mock_session_get.return_value = mock_response

        # Go to provider
        url = reverse("api-users:oauth_redirect")
        payload = {
            "provider": "google",
            "callback_url": "http://testserver" + reverse("core:health"),
            "process": process,
        }
        res = self.client.post(url, payload, format=None)
        self.assertEqual(res.status_code, status.HTTP_302_FOUND)

        # Come back from provider
        parsed_url = urlparse(res.url)
        query_params = parse_qs(parsed_url.query)
        url_state = query_params.get("state", [None])[0]
        self.assertIsNotNone(url_state)

        return_url = reverse("google_callback")
        return_url += f"?state={url_state}&code=testcode"

        res: JsonResponse = self.client.get(return_url, follow=True)
        mock_get_access_token.assert_called()
        mock_session_get.assert_called()
        self.assertResOk(res)

        # Check token in url
        parsed_res_url = urlparse(res.wsgi_request.get_full_path())
        res_query_params = parse_qs(parsed_res_url.query)
        token = res_query_params.get("token", None)
        error = res_query_params.get("error", None)
        self.assertIsNotNone(token, error)

        return token[0]

    def test_create_user_from_oauth(self):
        """Should create user via google sign in."""

        self.assertDoOauthFlow(return_email="john.doe@example.com")

        # Verify user was created
        self.assertEqual(User.objects.count(), 1)
        user = User.objects.first()
        self.assertEqual(user.email, "john.doe@example.com")

    def test_merge_user_accounts(self):
        """Should create user via google sign in."""

        personal_email = "john.doe@example.com"
        ufl_email = "jdoe@ufl.edu"

        # Initially created user using ufl email
        create_test_user(email=ufl_email)

        # User does oauth, registers with personal email
        self.assertDoOauthFlow(return_email=personal_email)
        self.assertEqual(User.objects.count(), 2)
        u2 = User.objects.get(email=personal_email)

        # Then, the user tries to verify ufl email
        verify_url = SEND_EMAIL_VERIFICATION_URL
        payload = {"email": ufl_email}
        self.client.force_authenticate(u2)
        res = self.client.post(verify_url, payload)
        self.assertResCreated(res)
        self.assertEmailsSent(1)

        self.assertEqual(EmailVerificationCode.objects.count(), 1)
        code = EmailVerificationCode.objects.first()

        # User successfully verifies email, showing they own it
        url = CHECK_EMAIL_VERIFICATION_URL
        payload = {"email": ufl_email, "code": code.code}
        res = self.client.post(url, payload)
        self.assertResCreated(res)

        # User accounts should have been merged, only one user exists
        self.assertEqual(User.objects.count(), 1)
        user = User.objects.first()
        self.assertEqual(user.email, personal_email)
        self.assertEqual(user.profile.school_email, ufl_email)
        self.assertTrue(user.profile.is_school_email_verified)

    def test_connect_existing_account_to_oauth(self):
        """Should connect oauth account to existing user."""

        # User is created by sys admin
        user = create_test_user()

        # Then, the created user goes to sign in via oauth
        with self.assertRaises(exceptions.AuthenticationFailed):
            self.assertDoOauthFlow(return_email=user.email)

        # Make sure no additional users were created
        self.assertEqual(User.objects.count(), 1)
