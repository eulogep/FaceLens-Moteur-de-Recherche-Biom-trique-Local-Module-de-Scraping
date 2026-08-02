import httpx
import trafilatura
from typing import Optional, Dict, Any

class ContextExtractor:
    """
    Extracts text context from HTML using trafilatura and handles downloading images.
    """
    @staticmethod
    def extract_page_text(html: str) -> str:
        try:
            text = trafilatura.extract(html)
            return text or ""
        except Exception:
            return ""

    @staticmethod
    async def download_image_bytes(image_url: str, timeout: float = 10.0) -> Optional[bytes]:
        try:
            async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
                headers = {"User-Agent": "FaceLensBot/1.0"}
                resp = await client.get(image_url, headers=headers)
                if resp.status_code == 200 and len(resp.content) > 1000:
                    return resp.content
                return None
        except Exception:
            return None
