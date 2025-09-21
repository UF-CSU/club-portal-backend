"""
Tests for the user API.
"""

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from core.abstracts.tests import EmailTestsBase, PrivateApiTestsBase, PublicApiTestsBase
from lib.faker import fake
from users.models import EmailVerificationCode
from users.tests.utils import CHECK_EMAIL_VERIFICATION_URL, SEND_EMAIL_VERIFICATION_URL

# CREATE_USER_URL = reverse("api-users:create")  # user as app, create as endpoint
LOGIN_TOKEN_URL = reverse("api-users:login")
ME_URL = reverse("api-users:me")


def create_user(**params):
    """Create and return a new user."""
    # create user with params
    return get_user_model().objects.create_user(**params)


class PublicUserApiTests(PublicApiTestsBase):
    """Test the public features of the user API."""

    def setUp(self):
        self.client = APIClient()

    # def test_create_user_success(self):
    #     """Test creating a user is successful."""
    #     payload = {  # content posted to url to create user
    #         "email": "test@example.com",
    #         "password": "testpass123",
    #     }
    #     res = self.client.post(CREATE_USER_URL, payload)

    #     # status 201 indicates successesful user creation
    #     self.assertEqual(res.status_code, status.HTTP_201_CREATED, res.data)
    #     user = get_user_model().objects.get(username=payload["email"])
    #     # securely check password with internal check method
    #     self.assertTrue(user.check_password(payload["password"]))
    #     # makes sure password not returned in api
    #     self.assertNotIn("password", res.data)

    # def test_user_with_email_exists_error(self):
    #     """Test error returned if user with email exists."""
    #     payload = {
    #         "email": "test@example.com",
    #         "password": "testpass123",
    #     }
    #     create_user(**payload)  # equal to email=email, password=password, etc
    #     # try creating user twice
    #     res = self.client.post(CREATE_USER_URL, payload)

    #     # should return status 400
    #     self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    # def test_password_too_short_error(self):
    #     """Test an error is returned if password less than 5 chars."""
    #     payload = {
    #         "email": "test@example.com",
    #         "password": "pw",
    #     }
    #     res = self.client.post(CREATE_USER_URL, payload)

    #     self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
    #     user_exists = (
    #         get_user_model().objects.filter(username=payload["email"]).exists()
    #     )  # make sure user isn't created in db
    #     self.assertFalse(user_exists)

    def test_create_token_for_user(self):
        """Test generates token for valid credentials."""
        user_details = {
            "email": "test@example.com",
            "password": "test-user-password123",
        }
        create_user(**user_details)

        payload = {  # sent to api in post
            "username": user_details["email"],
            "password": user_details["password"],
        }
        res = self.client.post(LOGIN_TOKEN_URL, payload)

        self.assertIn("token", res.data)  # res includes token
        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_create_token_bad_credentials(self):
        """Test returns error if credentials invalid."""
        create_user(email="test@example.com", password="goodpass")

        payload = {"username": "test@example.com", "password": "badpass"}
        res = self.client.post(LOGIN_TOKEN_URL, payload)

        self.assertNotIn("token", res.data)
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_token_blank_password(self):
        """Test posting a blank password returns an error."""
        payload = {"username": "test@example.com", "password": ""}
        res = self.client.post(LOGIN_TOKEN_URL, payload)

        self.assertNotIn("token", res.data)
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_retrieve_user_unauthorized(self):
        """Test authentication is required for users."""
        res = self.client.get(ME_URL)  # make unauthenticated request

        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class PrivateUserApiTests(PrivateApiTestsBase, EmailTestsBase):
    """Test API requests that require authentication"""

    # def setUp(self):
    #     self.user = create_user(
    #         email="test@example.com",
    #         password="testpass123",
    #     )
    #     self.client = APIClient()
    #     self.client.force_authenticate(user=self.user)

    def test_retrieve_profile_success(self):
        """Test retrieving profile for logged in user."""
        res = self.client.get(ME_URL)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn("email", res.data.keys())
        self.assertEqual(res.data["email"], self.user.email)

    def test_post_me_not_allowed(self):
        """Test POST is not allowed for the me endpoint"""
        # can only modify data with this endpoint, cannot create
        res = self.client.post(ME_URL, {})
        self.assertEqual(res.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_update_user_profile(self):
        """Test updating the user profile for the authenticated user."""
        payload = {"username": "test-username"}

        res = self.client.patch(ME_URL, payload)

        self.user.refresh_from_db()
        self.assertEqual(self.user.username, payload["username"])
        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_verify_user_email(self):
        """Should verify a user's email."""

        # Should request verification
        payload = {
            "email": self.user.email,
        }
        res = self.client.post(SEND_EMAIL_VERIFICATION_URL, payload)
        self.assertResCreated(res)

        self.assertEmailsSent(1)
        self.assertEqual(EmailVerificationCode.objects.count(), 1)
        vc = EmailVerificationCode.objects.first()
        self.assertInEmailBodies(vc.code)

        # Should unsuccessfully check wrong email
        payload = {
            "email": fake.email(),
            "code": vc.code,
        }
        res = self.client.post(CHECK_EMAIL_VERIFICATION_URL, payload)
        self.assertResBadRequest(res)

        # Should successfully check right email
        payload["email"] = self.user.email
        res = self.client.post(CHECK_EMAIL_VERIFICATION_URL, payload)
        self.assertResCreated(res)

        # Should reject duplicate request
        res = self.client.post(CHECK_EMAIL_VERIFICATION_URL, payload)
        self.assertResBadRequest(res)
