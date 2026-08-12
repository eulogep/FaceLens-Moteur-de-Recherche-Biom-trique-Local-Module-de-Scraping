from typing import Optional

import httpx
import trafilatura

from core.config import settings
from core.security import RemoteURLValidationError, validate_image_bytes, validate_public_http_url


class ContextExtractor:
    """Extracts public page text and safely downloads candidate image payloads."""

    @staticmethod
    def extract_page_text(html: str) -> str:
        try:
            return trafilatura.extract(html) or ""
        except (TypeError, ValueError):
            return ""

    @staticmethod
    async def download_image_bytes(image_url: str, timeout: float = 10.0) -> Optional[bytes]:
        """Fetch only validated public image data within a strict byte budget."""
        try:
            await validate_public_http_url(image_url)
            headers = {
                "User-Agent": "FaceLensBot/1.1",
                "Accept": "image/jpeg,image/png,image/webp",
            }
            async with httpx.AsyncClient(timeout=timeout, follow_redirects=False) as client:
                async with client.stream("GET", image_url, headers=headers) as response:
                    if response.is_redirect or response.status_code != 200:
                        return None
                    content_type = response.headers.get("content-type", "").split(";", 1)[0].lower()
                    if content_type not in {"image/jpeg", "image/png", "image/webp"}:
                        return None
                    chunks: list[bytes] = []
                    total = 0
                    async for chunk in response.aiter_bytes():
                        total += len(chunk)
                        if total > settings.MAX_REMOTE_IMAGE_BYTES:
                            return None
                        chunks.append(chunk)
            payload, _ = validate_image_bytes(b"".join(chunks), content_type)
            return payload
        except (RemoteURLValidationError, httpx.HTTPError, ValueError):
            return None
