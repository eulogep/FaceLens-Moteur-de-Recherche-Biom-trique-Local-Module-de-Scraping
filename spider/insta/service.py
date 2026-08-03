"""Public, anonymous Instagram ingestion pipeline."""

from __future__ import annotations

import json
import logging
import os
import random
import re
import tempfile
import threading
import time
import uuid
from collections.abc import Callable, Iterable
from typing import Any

import cv2
import httpx

from core.config import settings
from core.db import DatabaseManager
from core.face_engine import get_face_engine
from core.vector_index import VectorIndexManager
from spider.insta.client import InstagramPublicClient

logger = logging.getLogger("facelens.spider.insta")
_USERNAME_RE = re.compile(r"^[A-Za-z0-9._]{1,30}$")
_INSTAGRAM_JOB_LOCK = threading.Lock()


class InstagramIndexer:
    """Index public Instagram images through FaceLens' existing core pipeline."""

    def __init__(
        self,
        db: DatabaseManager,
        index: VectorIndexManager,
        *,
        client: InstagramPublicClient | None = None,
        engine_factory: Callable[[], Any] = get_face_engine,
        http_client_factory: Callable[[], httpx.Client] | None = None,
        sleep_fn: Callable[[float], None] = time.sleep,
        delay_range: tuple[float, float] = (2.0, 5.0),
    ) -> None:
        self.db = db
        self.index = index
        self.client = client or InstagramPublicClient()
        self.engine_factory = engine_factory
        self.http_client_factory = http_client_factory or self._default_http_client
        self.sleep_fn = sleep_fn
        self.delay_range = delay_range

    @staticmethod
    def _default_http_client() -> httpx.Client:
        return httpx.Client(
            follow_redirects=True,
            timeout=httpx.Timeout(30.0),
            headers={"User-Agent": "FaceLens/1.0 (public Instagram indexer)"},
        )

    @staticmethod
    def _username(username: str) -> str:
        value = username.strip().lstrip("@").lower()
        if not _USERNAME_RE.fullmatch(value):
            raise ValueError("Nom d'utilisateur Instagram invalide.")
        return value

    @staticmethod
    def _profile_metadata(user: Any) -> dict[str, Any]:
        return {
            "username": str(getattr(user, "username", "")),
            "pk": str(getattr(user, "pk", "")),
            "full_name": str(getattr(user, "full_name", "")),
            "bio": str(getattr(user, "biography", "") or ""),
            "is_private": bool(getattr(user, "is_private", False)),
            "is_verified": bool(getattr(user, "is_verified", False)),
        }

    @staticmethod
    def _profile_picture_url(user: Any) -> str:
        hd_info = getattr(user, "hd_profile_pic_url_info", None)
        hd_url = hd_info.get("url") if isinstance(hd_info, dict) else getattr(hd_info, "url", None)
        return str(
            hd_url
            or getattr(user, "profile_pic_url_hd", None)
            or getattr(user, "profile_pic_url", "")
        )

    @staticmethod
    def _media_url(media: Any) -> str:
        code = str(getattr(media, "code", ""))
        return f"https://www.instagram.com/p/{code}/" if code else "https://www.instagram.com/"

    @staticmethod
    def _iter_media_assets(media: Any) -> Iterable[tuple[str, str]]:
        media_type = int(getattr(media, "media_type", 0) or 0)
        if media_type == 8:
            for resource in getattr(media, "resources", []) or []:
                resource_type = int(getattr(resource, "media_type", 0) or 0)
                url = (
                    getattr(resource, "video_url", None)
                    if resource_type == 2
                    else getattr(resource, "thumbnail_url", None)
                )
                if url:
                    yield ("video" if resource_type == 2 else "image", str(url))
            return
        if media_type == 2 and getattr(media, "video_url", None):
            yield "video", str(media.video_url)
        elif getattr(media, "thumbnail_url", None):
            yield "image", str(media.thumbnail_url)

    @staticmethod
    def _exception_message(exc: Exception) -> str:
        if "429" in str(exc) or "too many 429" in str(exc).lower():
            return "Instagram public a répondu 429; job arrêté sans nouvelle tentative."
        messages = {
            "ClientThrottledError": "Instagram public a répondu 429; job arrêté sans nouvelle tentative.",
            "PleaseWaitFewMinutes": "Instagram demande une pause; job public arrêté proprement.",
            "FeedbackRequired": "Instagram refuse temporairement les requêtes; job arrêté proprement.",
            "ChallengeRequired": "La ressource exige une session; le mode public n'effectue aucune connexion.",
            "LoginRequired": "La ressource exige une session; le mode public n'effectue aucune connexion.",
        }
        return messages.get(type(exc).__name__, f"{type(exc).__name__}: {exc}")

    @staticmethod
    def _tags(metadata: dict[str, Any], **extra: Any) -> str:
        return json.dumps(
            {"instagram": metadata, **extra},
            ensure_ascii=False,
            separators=(",", ":"),
        )

    def _download(self, client: httpx.Client, url: str, *, max_bytes: int) -> bytes:
        response = client.get(url)
        response.raise_for_status()
        content = response.content
        if not content or len(content) > max_bytes:
            raise ValueError(f"Média vide ou supérieur à {max_bytes // (1024 * 1024)} Mo.")
        return content

    def _video_frames(self, content: bytes) -> Iterable[tuple[int, bytes]]:
        temp_path = ""
        try:
            with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as handle:
                handle.write(content)
                temp_path = handle.name
            capture = cv2.VideoCapture(temp_path)
            fps = float(capture.get(cv2.CAP_PROP_FPS) or 0.0)
            frame_step = max(1, round(fps * 2.0)) if fps > 0 else 50
            frame_number = 0
            try:
                while True:
                    ok, frame = capture.read()
                    if not ok:
                        break
                    if frame_number % frame_step == 0:
                        encoded, jpeg = cv2.imencode(".jpg", frame)
                        if encoded:
                            yield frame_number, jpeg.tobytes()
                    frame_number += 1
            finally:
                capture.release()
        finally:
            if temp_path and os.path.exists(temp_path):
                os.unlink(temp_path)

    def _index_image(
        self,
        image_bytes: bytes,
        *,
        source_url: str,
        metadata: dict[str, Any],
        extra_tags: dict[str, Any] | None = None,
    ) -> tuple[int, int]:
        indexed = 0
        duplicates = 0
        for face in self.engine_factory().extract_faces(image_bytes):
            vector = face["embedding"]
            top_matches = self.index.search(vector, top_k=1)
            if top_matches and top_matches[0][1] >= settings.THRESHOLD_DEDUP:
                duplicates += 1
                continue

            images_dir = os.path.join(settings.STORAGE_DIR, "images")
            os.makedirs(images_dir, exist_ok=True)
            saved_path = os.path.join(images_dir, f"instagram_{uuid.uuid4().hex}.jpg")
            with open(saved_path, "wb") as handle:
                handle.write(image_bytes)

            self.db.enroll_face_atomic(
                index_manager=self.index,
                vector=vector,
                image_path=saved_path,
                source_url=source_url,
                person_name=metadata["full_name"] or metadata["username"],
                source_type="instagram",
                tags=self._tags(metadata, **(extra_tags or {})),
                image_hash=face.get("phash"),
            )
            indexed += 1
        return indexed, duplicates

    def execute_profile_job(self, job_id: str, username: str) -> None:
        username = self._username(username)
        self.db.create_scrape_job(job_id, f"instagram://profile/{username}")
        self.db.update_scrape_job(job_id, status="running")
        with _INSTAGRAM_JOB_LOCK:
            try:
                user = self.client.user_info_by_username_public(username)
                metadata = self._profile_metadata(user)
                image_url = self._profile_picture_url(user)
                if not image_url:
                    raise ValueError("Instagram n'a fourni aucune photo de profil.")
                with self.http_client_factory() as http:
                    image = self._download(http, image_url, max_bytes=20 * 1024 * 1024)
                indexed, duplicates = self._index_image(
                    image,
                    source_url=f"https://www.instagram.com/{username}/",
                    metadata=metadata,
                    extra_tags={"kind": "profile_picture", "asset_url": image_url},
                )
                self.db.update_scrape_job(
                    job_id,
                    status="completed",
                    total_images=1,
                    faces_indexed=indexed,
                    duplicates_skipped=duplicates,
                )
            except Exception as exc:
                logger.warning("Instagram profile job %s stopped: %s", job_id, exc)
                self.db.update_scrape_job(
                    job_id,
                    status="partial",
                    errors_by_domain={"instagram.com": self._exception_message(exc)},
                )

    def execute_medias_job(self, job_id: str, username: str, amount: int = 10) -> None:
        username = self._username(username)
        self.db.create_scrape_job(job_id, f"instagram://medias/{username}")
        self.db.update_scrape_job(job_id, status="running")
        total_assets = 0
        indexed = 0
        duplicates = 0
        errors: dict[str, str] = {}

        with _INSTAGRAM_JOB_LOCK:
            try:
                user = self.client.user_info_by_username_public(username)
                metadata = self._profile_metadata(user)
                if metadata["is_private"]:
                    self.db.update_scrape_job(
                        job_id,
                        status="partial",
                        errors_by_domain={
                            "instagram.com": "Compte privé : aucun média demandé ni téléchargé."
                        },
                    )
                    return

                medias = self.client.user_medias_public(metadata["pk"], amount)
                with self.http_client_factory() as http:
                    for media in medias:
                        for asset_type, asset_url in self._iter_media_assets(media):
                            total_assets += 1
                            try:
                                content = self._download(
                                    http,
                                    asset_url,
                                    max_bytes=(
                                        100 * 1024 * 1024
                                        if asset_type == "video"
                                        else 20 * 1024 * 1024
                                    ),
                                )
                                samples = (
                                    self._video_frames(content)
                                    if asset_type == "video"
                                    else [(0, content)]
                                )
                                for frame_number, sample in samples:
                                    new_count, duplicate_count = self._index_image(
                                        sample,
                                        source_url=self._media_url(media),
                                        metadata=metadata,
                                        extra_tags={
                                            "kind": asset_type,
                                            "media_pk": str(getattr(media, "pk", "")),
                                            "frame": (
                                                frame_number
                                                if asset_type == "video"
                                                else None
                                            ),
                                            "asset_url": asset_url,
                                        },
                                    )
                                    indexed += new_count
                                    duplicates += duplicate_count
                            except Exception as exc:
                                errors[asset_url] = self._exception_message(exc)
                            self.sleep_fn(random.uniform(*self.delay_range))

                self.db.update_scrape_job(
                    job_id,
                    status="completed" if not errors else "partial",
                    total_images=total_assets,
                    faces_indexed=indexed,
                    duplicates_skipped=duplicates,
                    errors_by_domain=errors,
                )
            except Exception as exc:
                logger.warning("Instagram media job %s stopped: %s", job_id, exc)
                errors["instagram.com"] = self._exception_message(exc)
                self.db.update_scrape_job(
                    job_id,
                    status="partial",
                    total_images=total_assets,
                    faces_indexed=indexed,
                    duplicates_skipped=duplicates,
                    errors_by_domain=errors,
                )
