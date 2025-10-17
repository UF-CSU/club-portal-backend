from io import BytesIO
from unittest.mock import Mock

from django.core.files import File
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image

from lib.faker import fake
from utils.files import get_unique_filename


def create_test_image(width=100, height=100):
    """Create new image, return file path to image."""

    image = Image.new("RGB", size=(width, height), color=(155, 0, 0))
    name = get_unique_filename("test-image", ext="jpeg")
    buffer = BytesIO()

    image.save(buffer, "jpeg")
    buffer.seek(0)

    return File(buffer, name)


def create_test_uploadable_image(name=None, width=100, height=100):
    """Create new image, return SimpleUploadedFile format."""

    file = create_test_image(width=width, height=height)
    file_name = name or f"{fake.title().replace(' ', '_').lower()}.jpg"

    return SimpleUploadedFile(file_name, file.read(), content_type="image/jpeg")


def set_mock_return_image(mock_get):
    """Sets mock response to equal an image."""

    mock_get.return_value = Mock()
    mock_get.return_value.status_code = 200
    mock_get.return_value.content = fake.image((300, 300), "png")
    mock_get.return_value.headers = {"Content-Type": "image/png"}

    return mock_get
