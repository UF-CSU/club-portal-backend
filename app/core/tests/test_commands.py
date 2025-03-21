"""
Test custom Django management commands.
"""

import os
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.db.utils import OperationalError
from django.test import TestCase
from psycopg2 import OperationalError as Psycopg2Error  # type: ignore

User = get_user_model()


# mocking check command to simulate response
@patch("core.management.commands.wait_for_db.Command.check")
class CommandTests(TestCase):
    """Test commands."""

    def test_wait_for_db_ready(self, patched_check):
        """Test waiting for database if database ready."""
        # when check is called, just return true to mock ready
        patched_check.return_value = True

        # tests if db ready and if command is setup properly
        call_command("wait_for_db")

        patched_check.assert_called_once_with(databases=["default"])

    @patch("time.sleep")  # mocks sleep command so don't have to wait
    # add arguments from "inside-out"
    def test_wait_for_db_delay(self, patched_sleep, patched_check):
        """Test waiting for db when getting operationalError."""
        # mock raising an exception with .side_effect
        patched_check.side_effect = (
            [Psycopg2Error] * 2 + [OperationalError] * 3 + [True]
        )
        # first 2 times called, raise psycopg2error
        # then next 3 times raise operationalerror
        # need this to test catching both.
        # number of times called is variable/relative

        call_command("wait_for_db")

        # only call command 6 times (2 + 3 + 1)
        self.assertEqual(patched_check.call_count, 6)
        patched_check.assert_called_with(databases=["default"])

    @patch("core.management.commands.init_superuser.Command.check")
    def test_init_superuser_create(self, *args, **kwargs):
        """Should create new superuser."""

        self.assertEqual(User.objects.count(), 0)
        call_command("init_superuser")

        self.assertEqual(User.objects.count(), 1)

    @patch("core.management.commands.init_superuser.Command.check")
    def test_init_superuser_not_debug(self, *args, **kwargs):
        """Should not create super user if not debug mode."""

        os.environ["DJANGO_DEBUG"] = "0"
        call_command("init_superuser")

        self.assertEqual(User.objects.count(), 0)

    @patch("core.management.commands.init_superuser.Command.check")
    def test_init_superuser_exists(self, *args, **kwargs):
        """Should not create super user if one already exists."""

        email = os.environ.get("DJANGO_SUPERUSER_EMAIL")
        password = os.environ.get("DJANGO_SUPERUSER_PASS")

        email = "test-" + email  # Force different email
        User.objects.create_superuser(email=email, password=password)
        self.assertEqual(User.objects.count(), 1)

        call_command("init_superuser")
        self.assertEqual(User.objects.count(), 1)
