"""
Extended from django-debug-toolbar to include total query count
after each command.

Ref: https://github.com/django-commons/django-debug-toolbar/blob/main/debug_toolbar/management/commands/debugsqlshell.py
"""

import sys

from django.core.management.commands.shell import Command as BaseCommand
from django.db import connection

if connection.vendor == "postgresql":
    from django.db.backends.postgresql import base as base_module
else:
    from django.db.backends import utils as base_module

from debug_toolbar.management.commands.debugsqlshell import (
    PrintQueryWrapper as PrintQueryWrapperBase,
)

query_counter = 0


class Command(BaseCommand):
    def execute(self, *args, **options):
        global query_counter
        query_counter = 0

        # Display db query counter if there were any
        def post_display_hook(value):
            global query_counter
            if value is not None:
                # Print the original result
                print(repr(value))

            if query_counter > 0:
                print("Total queries:", query_counter)
                query_counter = 0  # Reset counter

        sys.displayhook = post_display_hook

        return super().execute(*args, **options)


class PrintQueryWrapper(PrintQueryWrapperBase):
    def execute(self, sql, params=()):
        global query_counter
        res = super().execute(sql, params)
        query_counter += 1
        return res


base_module.CursorDebugWrapper = PrintQueryWrapper
