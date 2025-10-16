import random
import uuid
from io import BytesIO

from django.core.files import File
from PIL import Image, ImageDraw


def create_default_icon(initials: str, image_path: str, fileprefix=None):
    """Create an icon for an object with a random background color and given initials in white text."""

    colors = [
        "#1A73E8",  # (Blue)
        "#34A853",  # (Green)
        "#EA4335",  # (Red)
        "#F9AB00",  # (Amber)
        "#8E24AA",  # (Purple)
        "#00ACC1",  # (Teal)
        "#FF7043",  # (Coral)
        "#3949AB",  # (Indigo)
        "#43A047",  # (Dark Green)
        "#D81B60",  # (Pink)
    ]

    color = random.choice(colors)
    fileprefix = fileprefix or initials

    img = Image.new("RGB", (300, 300), color=color)
    draw = ImageDraw.Draw(img)

    draw.text((150, 150), initials, fill="white", font_size=150, anchor="mm")

    # path = get_media_path(image_path, fileprefix=fileprefix, fileext="png")
    # img.save(path)
    filename = f"{fileprefix}-{uuid.uuid4()}.png"
    buffer = BytesIO()
    img.save(buffer, format="png")
    buffer.seek(0)

    file = File(buffer, name=filename)

    return file
