import asyncio
from io import BytesIO

import pytest
from PIL import Image

from core.config import Settings, settings
from core.security import (
    ImageValidationError,
    RemoteURLValidationError,
    require_api_key,
    validate_image_bytes,
    validate_public_http_url,
)
from spider.crawler import AsyncWebCrawler, PolitenessManager
from spider.extractor import ContextExtractor


def _png_payload(size: tuple[int, int] = (16, 16)) -> bytes:
    stream = BytesIO()
    Image.new("RGB", size, color=(12, 34, 56)).save(stream, format="PNG")
    return stream.getvalue()


def test_valid_image_is_accepted_with_canonical_extension():
    payload, extension = validate_image_bytes(_png_payload(), "image/png")
    assert payload.startswith(b"\x89PNG")
    assert extension == ".png"


def test_non_image_payload_is_rejected_with_domain_error():
    with pytest.raises(ImageValidationError) as error:
        validate_image_bytes(b"not an image", "image/jpeg")
    assert error.value.status_code == 400


def test_oversized_pixel_canvas_is_rejected_before_decode(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(settings, "MAX_IMAGE_PIXELS", 255)
    with pytest.raises(ImageValidationError) as error:
        validate_image_bytes(_png_payload((16, 16)), "image/png")
    assert error.value.status_code == 413


def test_cors_rejects_wildcard_and_parses_comma_separated_origins():
    key = "a" * 32
    with pytest.raises(ValueError):
        Settings(FACELENS_API_KEY=key, CORS_ORIGINS="*")
    parsed = Settings(
        FACELENS_API_KEY=key,
        CORS_ORIGINS="http://localhost:5173,http://127.0.0.1:5173",
    )
    assert parsed.CORS_ORIGINS == ("http://localhost:5173", "http://127.0.0.1:5173")


def test_invalid_api_key_is_rejected():
    with pytest.raises(Exception) as error:
        asyncio.run(require_api_key("incorrect-key"))
    assert getattr(error.value, "status_code", None) == 401


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


def test_politeness_normalizes_equivalent_origins_for_robots_and_rate_limits():
    manager = PolitenessManager()
    assert manager.get_domain("http://example.test:8080/page") == "example.test"
    assert manager.get_origin("https://EXAMPLE.test./page") == "https://example.test:443"
    assert manager.get_origin("https://example.test:0443/page") == "https://example.test:443"
    assert manager.get_origin("http://example.test:8080/page") == "http://example.test:8080"
    assert manager.get_semaphore("https://example.test:443") is manager.get_semaphore("https://example.test:443")
    assert manager.get_semaphore("https://example.test:443") is not manager.get_semaphore("https://example.test:444")


def test_static_biometric_directory_is_not_mounted():
    from app.main import app

    assert all(getattr(route, "path", None) != "/static/images" for route in app.routes)
