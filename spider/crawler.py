import asyncio
import random
import urllib.robotparser
from urllib.parse import urlparse, urljoin
import logging
import httpx
from bs4 import BeautifulSoup
from typing import List, Dict, Any, Optional, Set

logger = logging.getLogger("facelens.spider.crawler")

class PolitenessManager:
    def __init__(self):
        self.robot_parsers: Dict[str, urllib.robotparser.RobotFileParser] = {}
        self.domain_semaphores: Dict[str, asyncio.Semaphore] = {}
        self.user_agent = "FaceLensBot/1.0 (+http://localhost; public web indexer)"

    def get_domain(self, url: str) -> str:
        return urlparse(url).netloc.lower()

    async def can_fetch(self, url: str) -> bool:
        domain = self.get_domain(url)
        if domain not in self.robot_parsers:
            rp = urllib.robotparser.RobotFileParser()
            robots_url = f"{urlparse(url).scheme}://{domain}/robots.txt"
            try:
                async with httpx.AsyncClient(timeout=5.0) as client:
                    resp = await client.get(robots_url, headers={"User-Agent": self.user_agent})
                    if resp.status_code == 200:
                        rp.parse(resp.text.splitlines())
                    else:
                        rp.allow_all = True
            except Exception:
                rp.allow_all = True
            self.robot_parsers[domain] = rp

        return self.robot_parsers[domain].can_fetch(self.user_agent, url)

    def get_semaphore(self, domain: str) -> asyncio.Semaphore:
        if domain not in self.domain_semaphores:
            self.domain_semaphores[domain] = asyncio.Semaphore(3)
        return self.domain_semaphores[domain]

    async def delay(self):
        await asyncio.sleep(random.uniform(2.0, 5.0))

class AsyncWebCrawler:
    def __init__(self):
        self.politeness = PolitenessManager()

    async def fetch_page_images(self, url: str, max_images: int = 50) -> Dict[str, Any]:
        """
        Fetches web page using Playwright (or httpx fallback), scrolls page to trigger lazy-load,
        and extracts candidate image URLs with surrounding context metadata.
        """
        domain = self.politeness.get_domain(url)

        if not await self.politeness.can_fetch(url):
            return {
                "success": False,
                "url": url,
                "domain": domain,
                "error": f"Scraping interdit par robots.txt pour le domaine {domain}",
                "images": []
            }

        sem = self.politeness.get_semaphore(domain)
        async with sem:
            await self.politeness.delay()
            
            # Attempt Playwright first
            playwright_result = await self._fetch_with_playwright(url, max_images)
            if playwright_result["success"]:
                return playwright_result

            # Fallback to httpx + BeautifulSoup
            logger.info(f"Playwright non disponible ou échoué. Fallback HTTPX pour {url}")
            return await self._fetch_with_httpx(url, max_images)

    async def _fetch_with_playwright(self, url: str, max_images: int) -> Dict[str, Any]:
        domain = self.politeness.get_domain(url)
        try:
            from playwright.async_api import async_playwright
            async with async_playwright() as p:
                # Add --no-sandbox and container options for Docker reliability
                browser = await p.chromium.launch(
                    headless=True,
                    args=["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage"]
                )
                context = await browser.new_context(
                    user_agent=self.politeness.user_agent,
                    viewport={"width": 1280, "height": 800}
                )
                page = await context.new_page()
                
                response = await page.goto(url, wait_until="networkidle", timeout=30000)
                if response and response.status == 429:
                    await browser.close()
                    return {
                        "success": False,
                        "url": url,
                        "domain": domain,
                        "error": "HTTP 429 Too Many Requests (Rate limited)",
                        "images": []
                    }

                # Scroll to bottom to trigger lazy loading (data-src, srcset)
                await page.evaluate("""
                    async () => {
                        await new Promise((resolve) => {
                            let totalHeight = 0;
                            const distance = 300;
                            const timer = setInterval(() => {
                                const scrollHeight = document.body.scrollHeight;
                                window.scrollBy(0, distance);
                                totalHeight += distance;
                                if(totalHeight >= scrollHeight || totalHeight > 5000){
                                    clearInterval(timer);
                                    resolve();
                                }
                            }, 100);
                        });
                    }
                """)
                await page.wait_for_timeout(1000)

                html = await page.content()
                page_title = await page.title()
                await browser.close()

                images = self._extract_images_from_html(html, url, max_images)
                return {
                    "success": True,
                    "url": url,
                    "domain": domain,
                    "title": page_title,
                    "html": html,
                    "images": images,
                    "error": None
                }

        except Exception as e:
            return {
                "success": False,
                "url": url,
                "domain": domain,
                "error": str(e),
                "images": []
            }

    async def _fetch_with_httpx(self, url: str, max_images: int) -> Dict[str, Any]:
        domain = self.politeness.get_domain(url)
        try:
            headers = {"User-Agent": self.politeness.user_agent}
            async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
                resp = await client.get(url, headers=headers)
                if resp.status_code == 429:
                    return {
                        "success": False,
                        "url": url,
                        "domain": domain,
                        "error": "HTTP 429 Too Many Requests",
                        "images": []
                    }
                if resp.status_code != 200:
                    return {
                        "success": False,
                        "url": url,
                        "domain": domain,
                        "error": f"HTTP Error {resp.status_code}",
                        "images": []
                    }

                html = resp.text
                soup = BeautifulSoup(html, "lxml")
                page_title = soup.title.string if soup.title else url
                images = self._extract_images_from_html(html, url, max_images)
                return {
                    "success": True,
                    "url": url,
                    "domain": domain,
                    "title": page_title,
                    "html": html,
                    "images": images,
                    "error": None
                }
        except Exception as e:
            return {
                "success": False,
                "url": url,
                "domain": domain,
                "error": str(e),
                "images": []
            }

    def _extract_images_from_html(self, html: str, base_url: str, max_images: int) -> List[Dict[str, str]]:
        soup = BeautifulSoup(html, "lxml")
        seen_urls: Set[str] = set()
        image_list: List[Dict[str, str]] = []

        # Check OpenGraph image first
        og_img = soup.find("meta", property="og:image")
        if og_img and og_img.get("content"):
            full_url = urljoin(base_url, og_img["content"])
            seen_urls.add(full_url)
            image_list.append({"src": full_url, "context": "og:image"})

        # Check <img> tags
        for img in soup.find_all("img"):
            if len(image_list) >= max_images:
                break
            
            src = img.get("src") or img.get("data-src") or img.get("data-original")
            if not src or src.startswith("data:"):
                continue

            full_url = urljoin(base_url, src)

            # Filtering out default icons, avatars, tracking pixels
            low_url = full_url.lower()
            if any(term in low_url for term in ["avatar_default", "favicon", "1x1", "pixel", "logo_small"]):
                continue

            width = img.get("width")
            height = img.get("height")
            if width and width.isdigit() and int(width) < 100:
                continue
            if height and height.isdigit() and int(height) < 100:
                continue

            if full_url not in seen_urls:
                seen_urls.add(full_url)
                alt = img.get("alt", "")
                title = img.get("title", "")
                context = f"{alt} {title}".strip()
                image_list.append({"src": full_url, "context": context})

        return image_list
