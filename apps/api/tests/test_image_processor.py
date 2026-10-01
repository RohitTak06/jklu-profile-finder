from io import BytesIO

import pytest
from PIL import Image

from app.services.image_processor import InvalidImageError, normalize_image


def make_image(image_format: str = "PNG") -> bytes:
    output = BytesIO()
    Image.new("RGB", (24, 24), color=(30, 80, 60)).save(output, format=image_format)
    return output.getvalue()


def test_normalize_reencodes_supported_image_as_jpeg_without_metadata() -> None:
    normalized = normalize_image(make_image(), max_bytes=100_000, max_pixels=10_000)

    with Image.open(BytesIO(normalized)) as image:
        assert image.format == "JPEG"
        assert image.size == (24, 24)
        assert not image.getexif()


@pytest.mark.parametrize(
    ("data", "max_bytes", "max_pixels"),
    [
        (b"", 100_000, 10_000),
        (b"not an image", 100_000, 10_000),
        (make_image(), 2, 10_000),
        (make_image(), 100_000, 10),
    ],
)
def test_rejects_invalid_oversized_or_oversized_dimension_images(
    data: bytes, max_bytes: int, max_pixels: int
) -> None:
    with pytest.raises(InvalidImageError):
        normalize_image(data, max_bytes=max_bytes, max_pixels=max_pixels)