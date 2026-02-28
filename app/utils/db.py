from collections import namedtuple

from django.db.backends.utils import CursorWrapper


def dictfetchall(cursor: CursorWrapper):
    """
    Return all rows from a cursor as a dict.
    Assume the column names are unique.

    Ref: https://docs.djangoproject.com/en/5.2/topics/db/sql/#executing-custom-sql-directly
    """
    columns = [col[0] for col in cursor.description]
    return [dict(zip(columns, row, strict=False)) for row in cursor.fetchall()]


def dictfetchone(cursor: CursorWrapper):
    """
    Return first row from a cursor as a dict.
    Assume the column names are unique.

    Ref: https://docs.djangoproject.com/en/5.2/topics/db/sql/#executing-custom-sql-directly
    """
    columns = [col[0] for col in cursor.description]
    row = cursor.fetchone()

    if row is None:
        return None

    return dict(zip(columns, row, strict=False))


def namedtuplefetchall(cursor: CursorWrapper):
    """
    Return all rows from a cursor as a namedtuple.
    Assume the column names are unique.

    Ref: https://docs.djangoproject.com/en/5.2/topics/db/sql/#executing-custom-sql-directly
    """
    desc = cursor.description
    nt_result = namedtuple("Result", [col[0] for col in desc])
    return [nt_result(*row) for row in cursor.fetchall()]


def namedtuplefetchone(cursor: CursorWrapper):
    """
    Return first row from a cursor as a namedtuple.
    Assume the column names are unique.

    Ref: https://docs.djangoproject.com/en/5.2/topics/db/sql/#executing-custom-sql-directly
    """
    desc = cursor.description
    nt_result = namedtuple("Result", [col[0] for col in desc])
    return nt_result(*cursor.fetchone())
