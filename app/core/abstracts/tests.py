import os
from typing import Optional, Type

from django import forms
from django.core import mail
from django.http import HttpResponse
from django.test import TestCase
from django.urls import reverse
from rest_framework import serializers, status
from rest_framework.status import HTTP_200_OK
from rest_framework.test import APIClient

from users.tests.utils import create_test_adminuser


class TestsBase(TestCase):
    """Abstract testing utilities."""

    def assertObjFields(self, object, fields: dict):
        """Object fields should match given field values."""
        for key, value in fields.items():
            obj_value = getattr(object, key)
            self.assertEqual(obj_value, value)

    def assertNotImplemented(self):
        """Mark a test as not implemented, should fail."""
        self.fail("Method is not implemented.")

    def assertLength(self, target: list, length=1, msg=None):
        """Provided list should be specified length."""
        if msg is None:
            msg = f"Invalid length of {len(target)}, expected {length}."

        self.assertEqual(len(target), length, msg)

    def assertStartsWith(self, string: str, substring: str):
        """Target string should start with substring."""

        self.assertIsInstance(string, str)
        self.assertTrue(
            string.startswith(substring),
            f"String {string or 'EMPTY'} does not start with {substring}.",
        )

    def assertEndsWith(self, string: str, substring: str):
        """Target string should end with substring."""

        self.assertIsInstance(string, str)
        self.assertTrue(
            string.endswith(substring),
            f"String {string} does not end with {substring}.",
        )

    def assertFileExists(self, path):
        """File with path should exist."""

        self.assertTrue(os.path.exists(path), f"File does not exist at {path}.")

    def assertValidSerializer(self, serializer: serializers.Serializer):
        """Check `.is_valid()` function on serializer, prints errors if invalid."""

        self.assertTrue(serializer.is_valid(), serializer.errors)

    # def assertListEqual(self, list1: list, list2: list, msg=None, sort_lists=True):
    #     """Override default assertion to add sorting."""

    #     if sort_lists:
    #         list1.sort()
    #         list2.sort()

    #     return super().assertListEqual(list1, list2, msg)


class ApiTestsBase(TestsBase):
    """Abstract testing utilities for api testing."""

    def setUp(self):
        self.client = APIClient()

    def assertOk(self, reverse_url: str, reverse_kwargs=None):
        """The response for a reversed url should be 200 ok."""
        reverse_kwargs = reverse_kwargs if reverse_kwargs else {}
        url = reverse(reverse_url, **reverse_kwargs)
        res = self.client.get(url)

        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def assertStatusCode(
        self, response: HttpResponse, status_code: int, message=None, **kwargs
    ):
        """Http Response should have status code."""

        message = message if message else f"Responded with: {response.content}"
        self.assertEqual(response.status_code, status_code, message, **kwargs)

    def assertResOk(self, response: HttpResponse, **kwargs):
        """Client response should be 200."""

        self.assertStatusCode(response, status.HTTP_200_OK, **kwargs)

    def assertResCreated(self, response: HttpResponse, **kwargs):
        """Client response should be 201."""

        self.assertStatusCode(response, status.HTTP_201_CREATED, **kwargs)

    def assertResAccepted(self, response: HttpResponse, **kwargs):
        """Client response should be 202."""

        self.assertStatusCode(response, status.HTTP_202_ACCEPTED, **kwargs)

    def assertResUnauthorized(self, response: HttpResponse, **kwargs):
        """Client response should be 401."""

        self.assertStatusCode(response, status.HTTP_401_UNAUTHORIZED, **kwargs)


class AuthApiTestsBase(ApiTestsBase):
    """Testing utilities for apis where authentication is required."""

    def setUp(self):
        super().setUp()
        self.user = create_test_adminuser()

        self.client = APIClient()
        self.client.force_authenticate(user=self.user)


class ViewTestsBase(ApiTestsBase):
    """Abstract testing utilities for app views."""

    def assertRenders(
        self,
        url: Optional[str] = None,
        reverse_url: Optional[str] = None,
        *args,
        **kwargs,
    ):
        """Reversible url should return 200."""
        path = (
            reverse(reverse_url, args=[*args], kwargs={**kwargs})
            if reverse_url
            else url
        )
        assert path is not None

        res = self.client.get(path)
        self.assertEqual(res.status_code, HTTP_200_OK)

        return res

    def assertHasForm(
        self,
        res: HttpResponse,
        form_class: Type[forms.Form],
        initial_data: dict | None = None,
    ) -> forms.Form:
        """Response should have a form object."""

        form: forms.Form | None = res.context.get("form", None)
        self.assertIsInstance(form, form_class)
        assert form is not None

        if initial_data:
            for key, value in initial_data.items():
                if value:
                    self.assertIn(key, form.initial.keys())

                self.assertEqual(form.initial.get(key, None), value)

        return form


class AuthViewsTestsBase(ViewTestsBase):
    """Abstract testing utilities for app views that require auth."""

    def setUp(self):
        super().setUp()
        self.user = create_test_adminuser()
        self.user.is_superuser = True
        self.user.save()

        self.client = APIClient()
        self.client.force_authenticate(user=self.user)


class EmailTestsBase(TestsBase):
    """Testing utilities for sending emails."""

    def assertEmailsSent(self, count: int):
        """The email outbox length should equal given count."""

        self.assertEqual(len(mail.outbox), count)

    def assertInEmailBodies(self, substring: str):
        """The sent emails should include the substring in the email bodies."""

        for email in mail.outbox:
            body = email.body

            # Get all html attachments, most likely just one, and use them as body
            if isinstance(email, mail.EmailMultiAlternatives):
                bodies = [alt[0] for alt in email.alternatives if alt[1] == "text/html"]
                body = "\n".join(bodies)

            self.assertIn(substring, body)
