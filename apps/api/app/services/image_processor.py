from io import BytesIO

from PIL import Image, UnidentifiedImageError


class InvalidImageError(ValueError):
    pass


def normalize_image(data: bytes, max_bytes: int, max_pixels: int) -> bytes:
    if not data or len(data) > max_bytes:
        raise InvalidImageError("Image size is invalid")

    try:
        with Image.open(BytesIO(data)) as image:
            if image.format not in {"JPEG", "PNG", "WEBP"}:
                raise InvalidImageError("Unsupported image format")
            if image.width * image.height > max_pixels:
                raise InvalidImageError("Image dimensions exceed the allowed limit")
            image.load()
            normalized = image.convert("RGB")
            output = BytesIO()
            normalized.save(output, format="JPEG", quality=90, optimize=True)
            return output.getvalue()
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as error:
        raise InvalidImageError("Image could not be decoded") from error