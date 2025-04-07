import uuid
from pathlib import Path
from typing import Optional

from django.db import models

from app.settings import MEDIA_ROOT, S3_STORAGE_BACKEND

# def get_media_dir(nested_path=""):
#     return Path(MEDIA_ROOT, nested_path)


def get_media_path(
    nested_path="",
    filename: Optional[str] = None,
    fileprefix: Optional[str] = None,
    fileext: Optional[str] = None,
    create_path=True,
):
    """
    Get full directory path for media files.

    If filename is none, and fileprefix is provided, will create a unique filename
    with the given prefix.

    Parameters
    ----------
        - nested_path (str): Directory inside media root
        - filename (str): Name of the file inside directory
        - fileprefix (str): Used to generate unique filename in absence of filename.
        - fileext (str): File extension without dot, must be provided when using prefix.
        - create_path (bool): Automatically create nested directory structure if needed.
    """

    if nested_path.startswith("/"):
        nested_path = nested_path[1:]

    path = Path(MEDIA_ROOT, nested_path)

    if create_path:
        path.mkdir(parents=True, exist_ok=True)

    if filename:
        path = Path(path, filename)
    elif fileprefix or fileext:
        if fileprefix is None:
            # fileprefix = timezone.now().strftime("%d-%m-%Y_%H:%M:%S")
            fileprefix = "image"

        assert (
            fileext is not None
        ), "If using a file prefix, a file extension must also be provided."
        assert not fileext.startswith("."), "File extension must not start with a dot."

        filename = f"{fileprefix}-{uuid.uuid4()}.{fileext}"
        path = Path(path, filename)

    return str(path)


def get_file_path(file: models.FileField):
    """
    Returns the appropriate path for a file.

    In production, this returns file.url, and in development
    mode it returns file.path. This is because boto3 will
    raise an error if file.path is called in production.
    """

    if S3_STORAGE_BACKEND is True:
        return file.url
    else:
        return file.path
