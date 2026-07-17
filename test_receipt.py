import base64
import io

import pytest
from PIL import Image

import receipt


def _png_bytes(color=(200, 180, 160)) -> io.BytesIO:
    img = Image.new("RGB", (60, 40), color)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf


def test_prepare_image_returns_jpeg_base64():
    data_b64, media_type = receipt.prepare_image(_png_bytes())

    assert media_type == "image/jpeg"
    # the payload decodes and starts with the JPEG magic bytes
    decoded = base64.standard_b64decode(data_b64)
    assert decoded[:3] == b"\xff\xd8\xff"


def test_prepare_image_downscales_large_images():
    big = Image.new("RGB", (5000, 3000))
    buf = io.BytesIO()
    big.save(buf, format="PNG")
    buf.seek(0)

    data_b64, _ = receipt.prepare_image(buf)
    reloaded = Image.open(io.BytesIO(base64.standard_b64decode(data_b64)))
    assert max(reloaded.size) == receipt.MAX_IMAGE_EDGE


def test_prepare_image_rejects_non_images():
    with pytest.raises(receipt.ReceiptError):
        receipt.prepare_image(io.BytesIO(b"this is not an image"))


def test_extract_requires_api_key(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    assert receipt.is_configured() is False
    with pytest.raises(receipt.ReceiptError):
        receipt.extract_receipt("fakebase64", "image/jpeg")
