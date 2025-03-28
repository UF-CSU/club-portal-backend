"""
Django cmmand to wait for the database to be available
"""

import time

from django.core.management.base import BaseCommand
from django.db import connections
from django.db.utils import OperationalError
from psycopg2 import OperationalError as Psycopg2OpError  # type: ignore


class Command(BaseCommand):
    """Django command to wait for database"""

    def handle(self, *args, **options):
        """Entrypoint for command"""

        self.stdout.write("\nWaiting for database...")
        db_up = False
        while db_up is False:
            try:
                # Use default checks
                self.check(databases=["default"])

                # Manually check connection
                db = connections["default"]
                db.cursor()

                # If reached, db is connected
                db_up = True
            except (Psycopg2OpError, OperationalError):
                self.stdout.write("Database unavailable, waiting 1 second...")
                time.sleep(1)

        self.stdout.write(self.style.SUCCESS("Database available!"))
