import datetime
import json
import os
from typing import Literal, Optional

from django import forms
from django.core import mail
from django.http import HttpResponse
from django.test import TestCase
from django.urls import reverse
from django_celery_beat.models import PeriodicTask
from requests import Response
from rest_framework import serializers, status
from rest_framework.status import HTTP_200_OK
from rest_framework.test import APIClient

from core.abstracts.schedules import run_func
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

    def assertListEqual(self, list1: list, list2: list, sort_lists=False, msg=None):
        """Check if two lists are equal. Optionally sort the lists before checking."""

        if sort_lists:
            list1.sort()
            list2.sort()

        return super().assertListEqual(list1, list2, msg)

    def assertDatesEqual(
        self,
        date1: datetime.date | datetime.datetime,
        date2: datetime.date | datetime.datetime,
        skip: Optional[
            list[Literal["year", "month", "day", "hour", "minute", "second"]]
        ] = None,
    ):
        """
        Two dates should have the same year/month/day,
        and the same hour/min/sec if they are both `datetime` objects.
        """
        skip = skip or []
        if "year" not in skip:
            self.assertEqual(
                date1.year,
                date2.year,
                msg=f"Years do not match, {date1.year} != {date2.year}",
            )

        if "month" not in skip:
            self.assertEqual(
                date1.month,
                date2.month,
                msg=f"Months do not match, {date1.month} != {date2.month}",
            )
        if "day" not in skip:
            self.assertEqual(
                date1.day,
                date2.day,
                msg=f"Days do not match, {date1.day} != {date2.day}",
            )

        if isinstance(date1, datetime.datetime) and isinstance(
            date2, datetime.datetime
        ):
            if "hour" not in skip:
                self.assertEqual(
                    date1.hour,
                    date2.hour,
                    msg=f"Hours do not match, {date1.hour} != {date2.hour}",
                )
            if "minute" not in skip:
                self.assertEqual(
                    date1.minute,
                    date2.minute,
                    msg=f"Minutes do not match, {date1.minute} != {date2.minute}",
                )
            if "second" not in skip:
                self.assertEqual(
                    date1.second,
                    date2.second,
                    msg=f"Seconds do not match, {date1.second} != {date2.second}",
                )


class APIClientWrapper(APIClient):
    def get(self, path, data=None, follow=False, **extra) -> Response:
        return super().get(path, data, follow, **extra)

    def post(
        self, path, data=None, format="json", content_type=None, follow=False, **extra
    ) -> Response:
        return super().post(path, data, format, content_type, follow, **extra)

    def put(
        self, path, data=None, format="json", content_type=None, follow=False, **extra
    ) -> Response:
        return super().put(path, data, format, content_type, follow, **extra)

    def patch(
        self, path, data=None, format="json", content_type=None, follow=False, **extra
    ) -> Response:
        return super().patch(path, data, format, content_type, follow, **extra)

    def delete(
        self, path, data=None, format=None, content_type=None, follow=False, **extra
    ) -> Response:
        return super().delete(path, data, format, content_type, follow, **extra)


class PublicApiTestsBase(TestsBase):
    """Abstract testing utilities for api testing."""

    client: APIClientWrapper

    def setUp(self):
        self.client = APIClientWrapper()

    def assertOk(self, reverse_url: str, reverse_kwargs=None):
        """The response for a reversed url should be 200 ok."""
        reverse_kwargs = reverse_kwargs if reverse_kwargs else {}
        url = reverse(reverse_url, **reverse_kwargs)
        res = self.client.get(url)

        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def assertStatusCode(
        self, response: Response, status_code: int, message=None, **kwargs
    ):
        """Http Response should have status code."""

        if not message and hasattr(response, "content"):
            message = f"Responded with: {response.content}"
        elif not message:
            message = f"Responded with {response.status_code}"

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

    def assertResNoContent(self, response: HttpResponse, **kwargs):
        """Client response should be 204."""
        self.assertStatusCode(response, status.HTTP_204_NO_CONTENT, **kwargs)

    def assertResBadRequest(self, response: HttpResponse, **kwargs):
        """Client response should be 400"""
        self.assertStatusCode(response, status.HTTP_400_BAD_REQUEST, **kwargs)

    def assertResUnauthorized(self, response: HttpResponse, **kwargs):
        """Client response should be 401."""
        self.assertStatusCode(response, status.HTTP_401_UNAUTHORIZED, **kwargs)

    def assertResForbidden(self, response: HttpResponse, **kwargs):
        """Client response should be 403."""
        self.assertStatusCode(response, status.HTTP_403_FORBIDDEN, **kwargs)

    def assertResNotFound(self, response: HttpResponse, **kwargs):
        """Client response should be 404."""
        self.assertStatusCode(response, status.HTTP_404_NOT_FOUND, **kwargs)


class PrivateApiTestsBase(PublicApiTestsBase):
    """
    Testing utilities for apis where authentication is required.

    A user is automatically set in each request.
    """

    def create_authenticated_user(self):
        """Create the user that is authenticated in the api."""
        user = create_test_adminuser()
        user.is_superuser = True
        user.save()

        return user

    def setUp(self):
        super().setUp()

        self.user = self.create_authenticated_user()

        self.client = APIClientWrapper()
        self.client.force_authenticate(user=self.user)


class ViewTestsBase(PublicApiTestsBase):
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
        form_class: type[forms.Form],
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
                if len(bodies) > 0:
                    body = "\n".join(bodies)

            self.assertIn(substring, body)


class PeriodicTaskTestsBase(TestsBase):
    """Utilities for testing celery periodic tasks."""

    def mock_apply_sharedtask(self, fn: callable, args=None, kwargs=None):
        """Run a function with decorator @shared_task immediately, return output."""

        return fn.apply(args=args, kwargs=kwargs).get()

    def assertRunPeriodicTask(
        self, task: Optional[PeriodicTask] = None, check_params=None
    ):
        """Run periodic task."""

        if not task:
            task = PeriodicTask.objects.first()

            if task is None:
                self.fail("No task to run.")

        if check_params:
            self.assertPeriodicTaskKwargs(task, check_params)

        self.mock_apply_sharedtask(
            run_func, args=json.loads(task.args), kwargs=json.loads(task.kwargs)
        )

    def assertPeriodicTaskKwargs(self, task: PeriodicTask, expected_kwargs: dict):
        kwargs = json.loads(task.kwargs)
        # check_payload = {
        #     "max_runs": 1,
        #     **(expected_kwargs or {}),
        # }

        for key, value in expected_kwargs.items():
            self.assertEqual(
                kwargs[key],
                value,
                f"Expected kwargs[{key}] to be {value}, but got {kwargs[key]}.",
            )
