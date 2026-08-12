"""Validation helpers for untrusted uploads and remote URLs."""
from __future__ import annotations

import asyncio
import ipaddress
import socket
from io import BytesIO
from typing import Final
from urllib.parse import urlparse

from fastapi import HTTPException, UploadFile, status
from PIL import Image, UnidentifiedImageError

from core.config import settings

_ALLOWED_IMAGE_MEDIA_TYPES: Final[set[str]] = {
    "image/jpeg",
    "image/png",
    "image/webp",
}
_ALLOWED_IMAGE_FORMATS: Final[set[str]] = {"JPEG", "PNG", "WEBP"}
_EXTENSION_BY_FORMAT: Final[dict[str, str]] = {
    "JPEG": ".jpg",
    "PNG": ".png",
    "WEBP": ".webp",
}


class RemoteURLValidationError(ValueError):
    """Raised when a remote target is not safe for server-side fetching."""


def _bad_request(detail: str, status_code: int = status.HTTP_400_BAD_REQUEST) -> HTTPException:
    return HTTPException(status_code=status_code, detail=detail)


def validate_image_bytes(payload: bytes, declared_type: str | None = None) -> tuple[bytes, str]:
    """Validate and return a supported image payload and its safe extension."""
    if not payload:
        raise _bad_request("Le fichier image est vide.")
    if len(payload) > settings.MAX_IMAGE_UPLOAD_BYTES:
        raise _bad_request(
            f"Image trop volumineuse (maximum {settings.MAX_IMAGE_UPLOAD_BYTES} octets).",
            status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
        )
    if declared_type and declared_type.lower() not in _ALLOWED_IMAGE_MEDIA_TYPES:
        raise _bad_request("Type de fichier non autorisé. Utilisez JPEG, PNG ou WebP.")

    try:
        with Image.open(BytesIO(payload)) as image:
            image.verify()
        with Image.open(BytesIO(payload)) as image:
            image.load()
            image_format = (image.format or "").upper()
            pixel_count = image.width * image.height
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise _bad_request("Le contenu transmis n’est pas une image valide.") from exc

    if image_format not in _ALLOWED_IMAGE_FORMATS:
        raise _bad_request("Format image non autorisé. Utilisez JPEG, PNG ou WebP.")
    if pixel_count > settings.MAX_IMAGE_PIXELS:
        raise _bad_request(
            f"Image trop grande (maximum {settings.MAX_IMAGE_PIXELS} pixels).",
            status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
        )
    return payload, _EXTENSION_BY_FORMAT[image_format]


async def read_validated_upload(upload: UploadFile) -> tuple[bytes, str]:
    """Read an upload in bounded chunks, then validate its decoded image form."""
    declared_type = (upload.content_type or "").lower()
    if declared_type and declared_type not in _ALLOWED_IMAGE_MEDIA_TYPES:
        raise _bad_request("Type de fichier non autorisé. Utilisez JPEG, PNG ou WebP.")

    chunks: list[bytes] = []
    total = 0
    while True:
        chunk = await upload.read(min(64 * 1024, settings.MAX_IMAGE_UPLOAD_BYTES + 1))
        if not chunk:
            break
        total += len(chunk)
        if total > settings.MAX_IMAGE_UPLOAD_BYTES:
            raise _bad_request(
                f"Image trop volumineuse (maximum {settings.MAX_IMAGE_UPLOAD_BYTES} octets).",
                status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            )
        chunks.append(chunk)
    return validate_image_bytes(b"".join(chunks), declared_type or None)


def _is_public_address(address: str) -> bool:
    try:
        return ipaddress.ip_address(address).is_global
    except ValueError:
        return False


async def validate_public_http_url(url: str) -> str:
    """Ensure a URL resolves exclusively to globally routable HTTP(S) addresses."""
    try:
        parsed = urlparse(url.strip())
        port = parsed.port
    except ValueError as exc:
        raise RemoteURLValidationError("URL ou port invalide.") from exc

    if parsed.scheme not in {"http", "https"}:
        raise RemoteURLValidationError("Seules les URL HTTP et HTTPS sont autorisées.")
    if not parsed.hostname or parsed.username or parsed.password:
        raise RemoteURLValidationError("URL distante invalide.")

    host = parsed.hostname.rstrip(".").lower()
    if host == "localhost" or host.endswith(".localhost"):
        raise RemoteURLValidationError("Les hôtes locaux sont interdits.")

    try:
        literal = ipaddress.ip_address(host)
    except ValueError:
        literal = None
    if literal is not None:
        if not literal.is_global:
            raise RemoteURLValidationError("Les adresses privées, réservées ou locales sont interdites.")
        return url

    try:
        loop = asyncio.get_running_loop()
        addresses = await loop.getaddrinfo(
            host,
            port or (443 if parsed.scheme == "https" else 80),
            type=socket.SOCK_STREAM,
        )
    except (OSError, socket.gaierror) as exc:
        raise RemoteURLValidationError("Impossible de résoudre l’hôte distant.") from exc

    resolved = {entry[4][0] for entry in addresses}
    if not resolved or any(not _is_public_address(address) for address in resolved):
        raise RemoteURLValidationError("La destination distante n’est pas publiquement routable.")
    return url
