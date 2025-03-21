"""
Tests for the user API.
"""

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

CREATE_USER_URL = reverse("api-users:create")  # user as app, create as endpoint
LOGIN_TOKEN_URL = reverse("api-users:login")
ME_URL = reverse("api-users:me")


def create_user(**params):
    """Create and return a new user."""
    # create user with params
    return get_user_model().objects.create_user(**params)


class PublicUserApiTests(TestCase):
    """Test the public features of the user API."""

    def setUp(self):
        self.client = APIClient()

    def test_create_user_success(self):
        """Test creating a user is successful."""
        payload = {  # content posted to url to create user
            "email": "test@example.com",
            "password": "testpass123",
        }
        res = self.client.post(CREATE_USER_URL, payload)

        # status 201 indicates successesful user creation
        self.assertEqual(res.status_code, status.HTTP_201_CREATED, res.data)
        user = get_user_model().objects.get(username=payload["email"])
        # securely check password with internal check method
        self.assertTrue(user.check_password(payload["password"]))
        # makes sure password not returned in api
        self.assertNotIn("password", res.data)

    def test_user_with_email_exists_error(self):
        """Test error returned if user with email exists."""
        payload = {
            "email": "test@example.com",
            "password": "testpass123",
        }
        create_user(**payload)  # equal to email=email, password=password, etc
        # try creating user twice
        res = self.client.post(CREATE_USER_URL, payload)

        # should return status 400
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_password_too_short_error(self):
        """Test an error is returned if password less than 5 chars."""
        payload = {
            "email": "test@example.com",
            "password": "pw",
        }
        res = self.client.post(CREATE_USER_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        user_exists = (
            get_user_model().objects.filter(username=payload["email"]).exists()
        )  # make sure user isn't created in db
        self.assertFalse(user_exists)

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


class PrivateUserApiTests(TestCase):  # break out test bc auth is done before all tests
    """Test API requests that require authentication"""

    def setUp(self):
        self.user = create_user(
            email="test@example.com",
            password="testpass123",
        )
        self.client = APIClient()
        self.client.force_authenticate(
            user=self.user
        )  # force all requests to be authenticated

    def test_retrieve_profile_success(self):
        """Test retrieving profile for logged in user."""
        res = self.client.get(ME_URL)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn("email", res.data.keys())
        self.assertEqual(res.data["email"], self.user.email)
        # self.assertEqual(
        #     res.data,
        #     {
        #         "email": self.user.email,
        #     },
        # )

    def test_post_me_not_allowed(self):
        """Test POST is not allowed for the me endpoint"""
        # can only modify data with this endpoint, cannot create
        res = self.client.post(ME_URL, {})

        self.assertEqual(
            res.status_code, status.HTTP_405_METHOD_NOT_ALLOWED
        )  # post should only be used with create_user api

    def test_update_user_profile(self):
        """Test updating the user profile for the authenticated user."""
        payload = {"password": "newpassword123"}

        res = self.client.patch(ME_URL, payload)

        self.user.refresh_from_db()  # user data not refreshed automatically
        self.assertTrue(self.user.check_password(payload["password"]))
        self.assertEqual(res.status_code, status.HTTP_200_OK)
