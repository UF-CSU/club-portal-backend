from unittest.mock import Mock

from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image

from lib.faker import fake
from utils.files import get_media_path


def create_test_image(width=100, height=100):
    """Create new image, return file path to image."""

    image = Image.new("RGB", size=(width, height), color=(155, 0, 0))
    path = get_media_path("/temp/images", fileext="jpeg")
    image.save(path, "jpeg")

    return path


def create_test_uploadable_image(name=None, width=100, height=100):
    """Create new image, return SimpleUploadedFile format."""

    file_path = create_test_image(width=width, height=height)
    file_binary = open(file_path, mode="rb").read()
    file_name = name or "test_image.jpg"

    return SimpleUploadedFile(file_name, file_binary, content_type="image/jpeg")


def set_mock_return_image(mock_get):
    """Sets mock response to equal an image."""

    mock_get.return_value = Mock()
    mock_get.return_value.status_code = 200
    mock_get.return_value.content = fake.image((300, 300), "png")
    mock_get.return_value.headers = {"Content-Type": "image/png"}

    return mock_get
