from unittest.mock import Mock
from PIL import Image

from lib.faker import fake
from utils.files import get_media_path


def create_test_image(width=100, height=100):
    image = Image.new("RGB", size=(width, height), color=(155, 0, 0))
    path = get_media_path("/temp/images", fileext="jpeg")
    image.save(path, "jpeg")

    return path


def set_mock_return_image(mock_get):
    """Sets mock response to equal an image."""

    mock_get.return_value = Mock()
    mock_get.return_value.status_code = 200
    mock_get.return_value.content = fake.image((300, 300), "png")
    mock_get.return_value.headers = {"Content-Type": "image/png"}

    return mock_get
