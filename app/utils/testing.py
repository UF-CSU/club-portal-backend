from PIL import Image

from utils.files import get_media_path


def create_test_image(width=100, height=100):
    image = Image.new("RGB", size=(width, height), color=(155, 0, 0))
    path = get_media_path("/temp/images", fileext="jpeg")
    image.save(path, "jpeg")

    return path
