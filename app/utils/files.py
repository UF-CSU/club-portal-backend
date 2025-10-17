import uuid


def get_unique_filename(prefix: str, ext: str):
    """Get unique filename without path."""

    ext = ext.replace(".", "")

    return f"{prefix}-{uuid.uuid4()}.{ext}"
