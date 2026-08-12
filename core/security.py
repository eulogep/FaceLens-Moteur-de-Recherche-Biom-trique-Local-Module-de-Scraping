"""Security helpers for untrusted uploads and remote URLs.

Remote hostnames are checked before a fetch, but generic HTTP clients resolve DNS again
when opening their connection. This helper therefore reduces SSRF exposure but cannot,
by itself, guarantee protection against DNS rebinding for arbitrary hostnames. Deployments
requiring that guarantee must use an egress proxy or a transport that pins the validated IP.
"""
from __future__ import annotations

import asyncio
import hmac
import ipaddress
import socket
from io import BytesIO
from typing import Annotated, Final
from urllib.parse import urlparse

from fastapi import Header, HTTPException, UploadFile, status
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


class ImageValidationError(ValueError):
    """Raised when untrusted image content violates a domain validation rule."""

    def __init__(self, detail: str, status_code: int = status.HTTP_400_BAD_REQUEST):
        super().__init__(detail)
        self.detail = detail
        self.status_code = status_code


class RemoteURLValidationError(ValueError):
    """Raised when a remote target is not safe for server-side fetching."""


def image_validation_http_error(error: ImageValidationError) -> HTTPException:
    """Translate a domain validation error at the HTTP boundary only."""
    return HTTPException(status_code=error.status_code, detail=error.detail)


async def require_api_key(
    x_facelens_api_key: Annotated[str | None, Header()] = None,
) -> None:
    """Require the local operator API key for every biometric API route."""
    if not x_facelens_api_key or not hmac.compare_digest(
        x_facelens_api_key, settings.FACELENS_API_KEY
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Clé API FaceLens absente ou invalide.",
            headers={"WWW-Authenticate": "ApiKey"},
        )


def validate_image_bytes(
    payload: bytes,
    declared_type: str | None = None,
    *,
    max_bytes: int | None = None,
) -> tuple[bytes, str]:
    """Validate and return a supported image payload and its safe extension."""
    byte_limit = max_bytes if max_bytes is not None else settings.MAX_IMAGE_UPLOAD_BYTES
    if not payload:
        raise ImageValidationError("Le fichier image est vide.")
    if len(payload) > byte_limit:
        raise ImageValidationError(
            f"Image trop volumineuse (maximum {byte_limit} octets).",
            status.HTTP_413_CONTENT_TOO_LARGE,
        )
    if declared_type and declared_type.lower() not in _ALLOWED_IMAGE_MEDIA_TYPES:
        raise ImageValidationError("Type de fichier non autorisé. Utilisez JPEG, PNG ou WebP.")

    try:
        with Image.open(BytesIO(payload)) as image:
            image.verify()
        with Image.open(BytesIO(payload)) as image:
            image_format = (image.format or "").upper()
            pixel_count = image.width * image.height
            if pixel_count > settings.MAX_IMAGE_PIXELS:
                raise ImageValidationError(
                    f"Image trop grande (maximum {settings.MAX_IMAGE_PIXELS} pixels).",
                    status.HTTP_413_CONTENT_TOO_LARGE,
                )
            image.load()
    except ImageValidationError:
        raise
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise ImageValidationError("Le contenu transmis n’est pas une image valide.") from exc

    if image_format not in _ALLOWED_IMAGE_FORMATS:
        raise ImageValidationError("Format image non autorisé. Utilisez JPEG, PNG ou WebP.")
    return payload, _EXTENSION_BY_FORMAT[image_format]


async def read_validated_upload(
    upload: UploadFile,
    *,
    max_bytes: int | None = None,
) -> tuple[bytes, str]:
    """Read an upload in bounded chunks, then validate its decoded image form."""
    byte_limit = max_bytes if max_bytes is not None else settings.MAX_IMAGE_UPLOAD_BYTES
    declared_type = (upload.content_type or "").lower()
    try:
        if declared_type and declared_type not in _ALLOWED_IMAGE_MEDIA_TYPES:
            raise ImageValidationError("Type de fichier non autorisé. Utilisez JPEG, PNG ou WebP.")

        chunks: list[bytes] = []
        total = 0
        while True:
            chunk = await upload.read(min(64 * 1024, byte_limit + 1))
            if not chunk:
                break
            total += len(chunk)
            if total > byte_limit:
                raise ImageValidationError(
                    f"Image trop volumineuse (maximum {byte_limit} octets).",
                    status.HTTP_413_CONTENT_TOO_LARGE,
                )
            chunks.append(chunk)
        return validate_image_bytes(
            b"".join(chunks), declared_type or None, max_bytes=byte_limit
        )
    except ImageValidationError as exc:
        raise image_validation_http_error(exc) from exc


def _is_public_address(address: str) -> bool:
    try:
        return ipaddress.ip_address(address).is_global
    except ValueError:
        return False


async def validate_public_http_url(url: str) -> str:
    """Check a public HTTP(S) URL before fetching it.

    The resolved addresses are checked for global routability. A subsequent generic HTTP
    request may resolve the hostname again, so this function is not a complete DNS-rebinding
    defense unless the caller uses a transport or egress proxy that pins the validated address.
    """
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
