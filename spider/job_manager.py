import os
import uuid
import logging
import asyncio
from typing import Dict, Any, List, Optional
import numpy as np

from core.config import settings
from core.face_engine import get_face_engine
from core.vector_index import VectorIndexManager
from core.db import DatabaseManager
from spider.crawler import AsyncWebCrawler
from spider.extractor import ContextExtractor
from spider.searxng_client import SearXNGClient

logger = logging.getLogger("facelens.spider.job_manager")

class ScrapeJobManager:
    def __init__(self, db: DatabaseManager, index: VectorIndexManager):
        self.db = db
        self.index = index
        self.crawler = AsyncWebCrawler()
        self.searxng = SearXNGClient()

    async def execute_url_job(
        self,
        job_id: str,
        url: str,
        max_images: int = 50,
        source_type: str = "web",
        dry_run: bool = False
    ) -> None:
        """
        Executes a web scraping job for a given URL asynchronously.
        """
        self.db.create_scrape_job(job_id, url)
        self.db.update_scrape_job(job_id, status="running")

        domain = self.crawler.politeness.get_domain(url)
        errors_by_domain: Dict[str, str] = {}

        # Check domain exclusion
        if self.db.is_domain_excluded(domain):
            errors_by_domain[domain] = "Domaine dans la liste noire d'exclusion"
            self.db.update_scrape_job(
                job_id,
                status="failed",
                errors_by_domain=errors_by_domain
            )
            return

        crawl_result = await self.crawler.fetch_page_images(url, max_images)
        if not crawl_result["success"]:
            errors_by_domain[domain] = crawl_result["error"] or "Erreur de crawl"
            self.db.update_scrape_job(
                job_id,
                status="failed",
                errors_by_domain=errors_by_domain
            )
            return

        image_items = crawl_result["images"]
        total_images = len(image_items)
        faces_indexed = 0
        duplicates_skipped = 0

        engine = get_face_engine()

        for item in image_items:
            img_url = item["src"]
            context_text = item.get("context", "")

            # Download image bytes
            img_bytes = await ContextExtractor.download_image_bytes(img_url)
            if not img_bytes:
                continue

            # Detect faces
            try:
                detected_faces = engine.extract_faces(img_bytes)
            except Exception as e:
                logger.warning(f"Error detecting faces in {img_url}: {e}")
                continue

            if not detected_faces:
                continue  # Ignore images with 0 faces

            for face in detected_faces:
                vector = face["embedding"]
                phash = face["phash"]

                # Deduplication check via FAISS top-1 search
                top_matches = self.index.search(vector, top_k=1)
                if top_matches:
                    top_sim = top_matches[0][1]
                    if top_sim >= settings.THRESHOLD_DEDUP:
                        duplicates_skipped += 1
                        continue

                if dry_run:
                    faces_indexed += 1
                    continue

                # Save face image to local storage
                ext = ".jpg"
                filename = f"scraped_{uuid.uuid4().hex}{ext}"
                images_dir = os.path.join(settings.STORAGE_DIR, "images")
                os.makedirs(images_dir, exist_ok=True)
                saved_path = os.path.join(images_dir, filename)

                with open(saved_path, "wb") as f:
                    f.write(img_bytes)

                # Atomic enrollment into SQLite and FAISS
                try:
                    self.db.enroll_face_atomic(
                        index_manager=self.index,
                        vector=vector,
                        image_path=saved_path,
                        source_url=img_url,
                        person_name=context_text[:100] if context_text else None,
                        source_type=source_type,
                        tags=f"domain:{domain},job:{job_id}",
                        image_hash=phash
                    )
                    faces_indexed += 1
                except Exception as e:
                    logger.error(f"Atomic enrollment failed for {img_url}: {e}")
                    errors_by_domain[domain] = f"Erreur d'indexation: {e}"

        final_status = "completed" if not errors_by_domain else "partial"
        self.db.update_scrape_job(
            job_id=job_id,
            status=final_status,
            total_images=total_images,
            faces_indexed=faces_indexed,
            duplicates_skipped=duplicates_skipped,
            errors_by_domain=errors_by_domain
        )

    async def execute_searxng_job(
        self,
        job_id: str,
        query: str,
        limit: int = 20,
        dry_run: bool = False
    ) -> None:
        """
        Executes a SearXNG image search scrape job.
        """
        self.db.create_scrape_job(job_id, f"searxng://{query}")
        self.db.update_scrape_job(job_id, status="running")

        searxng_resp = await self.searxng.search_images(query, limit=limit)
        errors_by_domain: Dict[str, str] = {}

        if not searxng_resp["success"]:
            errors_by_domain["searxng"] = searxng_resp["error"]
            self.db.update_scrape_job(
                job_id,
                status="failed",
                errors_by_domain=errors_by_domain
            )
            return

        results = searxng_resp["results"]
        total_images = len(results)
        faces_indexed = 0
        duplicates_skipped = 0

        engine = get_face_engine()

        for item in results:
            img_url = item["img_src"]
            title = item.get("title", "")
            domain = self.crawler.politeness.get_domain(img_url) or "searxng"

            if self.db.is_domain_excluded(domain):
                errors_by_domain[domain] = "Domaine dans la liste noire d'exclusion"
                continue

            img_bytes = await ContextExtractor.download_image_bytes(img_url)
            if not img_bytes:
                continue

            try:
                detected_faces = engine.extract_faces(img_bytes)
            except Exception:
                continue

            if not detected_faces:
                continue

            for face in detected_faces:
                vector = face["embedding"]
                phash = face["phash"]

                top_matches = self.index.search(vector, top_k=1)
                if top_matches and top_matches[0][1] >= settings.THRESHOLD_DEDUP:
                    duplicates_skipped += 1
                    continue

                if dry_run:
                    faces_indexed += 1
                    continue

                ext = ".jpg"
                filename = f"searxng_{uuid.uuid4().hex}{ext}"
                images_dir = os.path.join(settings.STORAGE_DIR, "images")
                os.makedirs(images_dir, exist_ok=True)
                saved_path = os.path.join(images_dir, filename)

                with open(saved_path, "wb") as f:
                    f.write(img_bytes)

                try:
                    self.db.enroll_face_atomic(
                        index_manager=self.index,
                        vector=vector,
                        image_path=saved_path,
                        source_url=img_url,
                        person_name=title[:100] if title else None,
                        source_type="searxng",
                        tags=f"query:{query},domain:{domain}",
                        image_hash=phash
                    )
                    faces_indexed += 1
                except Exception as e:
                    errors_by_domain[domain] = f"Erreur d'indexation: {e}"

        final_status = "completed" if not errors_by_domain else "partial"
        self.db.update_scrape_job(
            job_id=job_id,
            status=final_status,
            total_images=total_images,
            faces_indexed=faces_indexed,
            duplicates_skipped=duplicates_skipped,
            errors_by_domain=errors_by_domain
        )
