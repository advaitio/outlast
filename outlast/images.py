from __future__ import annotations

from io import BytesIO

from PIL import Image, ImageOps, UnidentifiedImageError


def image_for_display(source: bytes | str) -> Image.Image | bytes | str:
    """Apply embedded camera orientation to byte-backed images without cropping them."""
    if not isinstance(source, bytes):
        return source

    try:
        with Image.open(BytesIO(source)) as uploaded:
            return ImageOps.exif_transpose(uploaded).copy()
    except (OSError, UnidentifiedImageError):
        return source
