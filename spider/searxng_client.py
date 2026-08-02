import httpx
import logging
from typing import List, Dict, Any
from core.config import settings

logger = logging.getLogger("facelens.spider.searxng")

class SearXNGClient:
    """
    Client for interacting with local SearXNG Docker service via HTTP REST API.
    CRITICAL: Does NOT import SearXNG python packages, strictly relies on HTTP calls.
    """
    def __init__(self, base_url: str = settings.SEARXNG_URL):
        self.base_url = base_url.rstrip("/")

    async def search_images(self, query: str, limit: int = 20) -> Dict[str, Any]:
        """
        Executes an image search query on SearXNG.
        Endpoint: /search?q={query}&categories=images&format=json
        """
        url = f"{self.base_url}/search"
        params = {
            "q": query,
            "categories": "images",
            "format": "json"
        }
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(url, params=params)
                if resp.status_code != 200:
                    logger.warning(f"SearXNG HTTP error {resp.status_code} for query '{query}'")
                    return {
                        "success": False,
                        "error": f"SearXNG returned HTTP {resp.status_code}",
                        "results": []
                    }
                
                data = resp.json()
                results = data.get("results", [])
                
                formatted_results = []
                for item in results[:limit]:
                    formatted_results.append({
                        "img_src": item.get("img_src") or item.get("url"),
                        "title": item.get("title", ""),
                        "source_url": item.get("url", ""),
                        "engine": item.get("engine", "searxng")
                    })

                return {
                    "success": True,
                    "query": query,
                    "total": len(formatted_results),
                    "results": formatted_results,
                    "error": None
                }

        except Exception as e:
            logger.error(f"Failed to connect to SearXNG at {self.base_url}: {e}")
            return {
                "success": False,
                "error": f"Connexion à SearXNG échouée ({e})",
                "results": []
            }
