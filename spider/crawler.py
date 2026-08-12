import asyncio
import logging
import random
import urllib.robotparser
from typing import Any, Dict, List, Set
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup

from core.config import settings
from core.security import RemoteURLValidationError, validate_public_http_url

logger = logging.getLogger("facelens.spider.crawler")


class PolitenessManager:
    def __init__(self) -> None:
        self.robot_parsers: Dict[str, urllib.robotparser.RobotFileParser] = {}
        self.origin_semaphores: Dict[str, asyncio.Semaphore] = {}
        self.user_agent = "FaceLensBot/1.2 (+local self-hosted indexer)"

    def get_domain(self, url: str) -> str:
        """Return only the hostname for user-facing reporting."""
        return (urlparse(url).hostname or "").lower()

    def get_origin(self, url: str) -> str:
        """Return the scheme and netloc so ports never collapse between origins."""
        parsed = urlparse(url)
        return f"{parsed.scheme}://{parsed.netloc.lower()}"

    async def _get_robots_response(
        self,
        client: httpx.AsyncClient,
        robots_url: str,
    ) -> httpx.Response:
        response = await client.get(robots_url, headers={"User-Agent": self.user_agent})
        if not response.is_redirect:
            return response
        target = urljoin(robots_url, response.headers.get("location", ""))
        await validate_public_http_url(target)
        return await client.get(target, headers={"User-Agent": self.user_agent})

    async def can_fetch(self, url: str) -> bool:
        origin = self.get_origin(url)
        if origin in self.robot_parsers:
            return self.robot_parsers[origin].can_fetch(self.user_agent, url)

        parser = urllib.robotparser.RobotFileParser()
        robots_url = f"{origin}/robots.txt"
        try:
            async with httpx.AsyncClient(timeout=5.0, follow_redirects=False) as client:
                response = await self._get_robots_response(client, robots_url)
            if response.status_code == 200 and len(response.content) <= 512 * 1024:
                parser.parse(response.text.splitlines())
            elif response.status_code == 404:
                parser.allow_all = True
            else:
                parser.disallow_all = True
        except (httpx.HTTPError, RemoteURLValidationError):
            parser.disallow_all = True
        self.robot_parsers[origin] = parser
        return parser.can_fetch(self.user_agent, url)

    def get_semaphore(self, origin: str) -> asyncio.Semaphore:
        if origin not in self.origin_semaphores:
            self.origin_semaphores[origin] = asyncio.Semaphore(2)
        return self.origin_semaphores[origin]

    async def delay(self) -> None:
        await asyncio.sleep(random.uniform(2.0, 5.0))


class AsyncWebCrawler:
    def __init__(self) -> None:
        self.politeness = PolitenessManager()

    async def fetch_page_images(self, url: str, max_images: int = 50) -> Dict[str, Any]:
        """Fetch public HTML after validation and robots authorization.

        Generic HTTP clients may resolve a hostname again after validation. The default
        strict mode therefore uses HTTPX without redirects and should remain enabled;
        deployments needing hard DNS-rebinding guarantees need an egress proxy or a
        transport that pins validated IP addresses.
        """
        try:
            await validate_public_http_url(url)
        except RemoteURLValidationError as exc:
            return {
                "success": False,
                "url": url,
                "domain": self.politeness.get_domain(url),
                "error": f"URL refusée: {exc}",
                "images": [],
            }

        domain = self.politeness.get_domain(url)
        origin = self.politeness.get_origin(url)
        if not await self.politeness.can_fetch(url):
            return {
                "success": False,
                "url": url,
                "domain": domain,
                "error": f"Scraping interdit ou non vérifiable par robots.txt pour le domaine {domain}",
                "images": [],
            }

        async with self.politeness.get_semaphore(origin):
            await self.politeness.delay()
            if settings.STRICT_REMOTE_URL_VALIDATION:
                return await self._fetch_with_httpx(url, max_images)
            logger.warning(
                "Playwright mode follows browser redirects and cannot provide a complete SSRF guarantee."
            )
            playwright_result = await self._fetch_with_playwright(url, max_images)
            if playwright_result["success"]:
                return playwright_result
            logger.info("Playwright indisponible ou en erreur; fallback HTTPX sécurisé.")
            return await self._fetch_with_httpx(url, max_images)

    async def _fetch_with_playwright(self, url: str, max_images: int) -> Dict[str, Any]:
        domain = self.politeness.get_domain(url)
        try:
            from playwright.async_api import async_playwright

            async with async_playwright() as playwright:
                browser = await playwright.chromium.launch(
                    headless=True,
                    args=["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage"],
                )
                try:
                    context = await browser.new_context(
                        user_agent=self.politeness.user_agent,
                        viewport={"width": 1280, "height": 800},
                    )
                    page = await context.new_page()
                    response = await page.goto(url, wait_until="networkidle", timeout=30_000)
                    if not response or response.status != 200:
                        return {
                            "success": False,
                            "url": url,
                            "domain": domain,
                            "error": "Erreur de chargement Playwright.",
                            "images": [],
                        }
                    await validate_public_http_url(page.url)
                    html = await page.content()
                    title = await page.title()
                    return {
                        "success": True,
                        "url": url,
                        "domain": domain,
                        "title": title,
                        "html": html,
                        "images": self._extract_images_from_html(html, url, max_images),
                        "error": None,
                    }
                finally:
                    await browser.close()
        except Exception as exc:
            logger.warning("Playwright fetch failed for %s: %s", domain, exc)
            return {"success": False, "url": url, "domain": domain, "error": str(exc), "images": []}

    async def _fetch_with_httpx(self, url: str, max_images: int) -> Dict[str, Any]:
        domain = self.politeness.get_domain(url)
        try:
            headers = {
                "User-Agent": self.politeness.user_agent,
                "Accept": "text/html,application/xhtml+xml",
            }
            async with httpx.AsyncClient(timeout=15.0, follow_redirects=False) as client:
                async with client.stream("GET", url, headers=headers) as response:
                    if response.is_redirect:
                        return {
                            "success": False,
                            "url": url,
                            "domain": domain,
                            "error": "Redirection distante refusée.",
                            "images": [],
                        }
                    if response.status_code != 200:
                        return {
                            "success": False,
                            "url": url,
                            "domain": domain,
                            "error": f"HTTP Error {response.status_code}",
                            "images": [],
                        }
                    content_type = response.headers.get("content-type", "").lower()
                    if "text/html" not in content_type and "application/xhtml+xml" not in content_type:
                        return {
                            "success": False,
                            "url": url,
                            "domain": domain,
                            "error": "La ressource distante n’est pas une page HTML.",
                            "images": [],
                        }
                    chunks: list[bytes] = []
                    total = 0
                    async for chunk in response.aiter_bytes():
                        total += len(chunk)
                        if total > settings.MAX_REMOTE_IMAGE_BYTES:
                            return {
                                "success": False,
                                "url": url,
                                "domain": domain,
                                "error": "Page distante trop volumineuse.",
                                "images": [],
                            }
                        chunks.append(chunk)
            html = b"".join(chunks).decode("utf-8", errors="replace")
            soup = BeautifulSoup(html, "lxml")
            return {
                "success": True,
                "url": url,
                "domain": domain,
                "title": soup.title.string.strip() if soup.title and soup.title.string else url,
                "html": html,
                "images": self._extract_images_from_html(html, url, max_images),
                "error": None,
            }
        except httpx.HTTPError as exc:
            return {"success": False, "url": url, "domain": domain, "error": str(exc), "images": []}

    def _extract_images_from_html(self, html: str, base_url: str, max_images: int) -> List[Dict[str, str]]:
        soup = BeautifulSoup(html, "lxml")
        seen_urls: Set[str] = set()
        images: List[Dict[str, str]] = []

        def add_image(src: str, context: str) -> None:
            if len(images) >= max_images or not src or src.startswith("data:"):
                return
            full_url = urljoin(base_url, src)
            parsed = urlparse(full_url)
            if parsed.scheme not in {"http", "https"} or not parsed.hostname:
                return
            low_url = full_url.lower()
            if any(token in low_url for token in ["avatar_default", "favicon", "1x1", "pixel", "logo_small"]):
                return
            if full_url not in seen_urls:
                seen_urls.add(full_url)
                images.append({"src": full_url, "context": context})

        og_image = soup.find("meta", property="og:image")
        if og_image and og_image.get("content"):
            add_image(og_image["content"], "og:image")
        for image in soup.find_all("img"):
            width, height = image.get("width"), image.get("height")
            if width and width.isdigit() and int(width) < 100:
                continue
            if height and height.isdigit() and int(height) < 100:
                continue
            add_image(
                image.get("src") or image.get("data-src") or image.get("data-original") or "",
                f"{image.get('alt', '')} {image.get('title', '')}".strip(),
            )
        return images
