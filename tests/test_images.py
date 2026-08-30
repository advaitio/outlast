from __future__ import annotations

from io import BytesIO

from PIL import Image

from outlast.images import image_for_display


def test_image_for_display_applies_exif_orientation_without_cropping() -> None:
    source = Image.new("RGB", (2, 3), "white")
    exif = source.getexif()
    exif[274] = 6
    encoded = BytesIO()
    source.save(encoded, format="JPEG", exif=exif)

    displayed = image_for_display(encoded.getvalue())

    assert isinstance(displayed, Image.Image)
    assert displayed.size == (3, 2)


def test_image_for_display_leaves_urls_unchanged() -> None:
    url = "https://example.com/repair-photo.jpg"

    assert image_for_display(url) == url


def test_image_for_display_falls_back_for_invalid_bytes() -> None:
    source = b"not-an-image"

    assert image_for_display(source) == source
