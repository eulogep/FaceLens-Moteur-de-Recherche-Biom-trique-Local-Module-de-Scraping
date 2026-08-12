import asyncio
from io import BytesIO

import pytest
from PIL import Image

from core.security import (
    RemoteURLValidationError,
    validate_image_bytes,
    validate_public_http_url,
)
from spider.crawler import AsyncWebCrawler
from spider.extractor import ContextExtractor


def _png_payload() -> bytes:
    stream = BytesIO()
    Image.new("RGB", (16, 16), color=(12, 34, 56)).save(stream, format="PNG")
    return stream.getvalue()


def test_valid_image_is_accepted_with_canonical_extension():
    payload, extension = validate_image_bytes(_png_payload(), "image/png")
    assert payload.startswith(b"\x89PNG")
    assert extension == ".png"


def test_non_image_payload_is_rejected():
    with pytest.raises(Exception) as error:
        validate_image_bytes(b"not an image", "image/jpeg")
    assert getattr(error.value, "status_code", None) == 400


def test_private_and_non_http_targets_are_rejected_without_network_access():
    for target in ("http://127.0.0.1/admin", "http://[::1]/", "file:///etc/passwd"):
        with pytest.raises(RemoteURLValidationError):
            asyncio.run(validate_public_http_url(target))


def test_crawler_rejects_private_url_before_fetching():
    result = asyncio.run(AsyncWebCrawler().fetch_page_images("http://127.0.0.1/private"))
    assert result["success"] is False
    assert "URL refusée" in result["error"]


def test_remote_image_downloader_rejects_private_url_before_fetching():
    result = asyncio.run(ContextExtractor.download_image_bytes("http://127.0.0.1/private.png"))
    assert result is None
