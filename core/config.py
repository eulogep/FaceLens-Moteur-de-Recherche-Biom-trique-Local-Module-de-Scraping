from __future__ import annotations

import os
from typing import Annotated
from urllib.parse import urlparse

from pydantic import AliasChoices, Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    # InsightFace configuration
    INSIGHTFACE_MODEL: str = Field(
        default="buffalo_l",
        validation_alias=AliasChoices("INSIGHTFACE_MODEL", "MODEL_NAME"),
    )
    INSIGHTFACE_CTX_ID: int = Field(
        default=-1,
        validation_alias=AliasChoices("INSIGHTFACE_CTX_ID", "CTX_ID"),
    )
    INSIGHTFACE_DET_SIZE: tuple[int, int] = (640, 640)
    INSIGHTFACE_DET_THRESH: float = Field(
        default=0.5,
        validation_alias=AliasChoices("INSIGHTFACE_DET_THRESH", "DET_THRESH_DEFAULT"),
    )
    INSIGHTFACE_DET_THRESH_FALLBACK: float = Field(
        default=0.4,
        validation_alias=AliasChoices(
            "INSIGHTFACE_DET_THRESH_FALLBACK", "DET_THRESH_FALLBACK"
        ),
    )

    # Similarity thresholds (cosine similarity in [0.0, 1.0])
    THRESHOLD_STRONG: float = Field(
        default=0.70,
        validation_alias=AliasChoices("THRESHOLD_STRONG", "SIMILARITY_STRONG"),
    )
    THRESHOLD_MEDIUM: float = Field(
        default=0.50,
        validation_alias=AliasChoices("THRESHOLD_MEDIUM", "SIMILARITY_MEDIUM"),
    )
    THRESHOLD_LOOKALIKE: float = 0.50
    THRESHOLD_DEDUP: float = Field(
        default=0.95,
        validation_alias=AliasChoices("THRESHOLD_DEDUP", "DEDUP_THRESHOLD"),
    )

    # Local API protection and network limits
    FACELENS_API_KEY: str = Field(min_length=32, repr=False)
    FACELENS_PORT: int = 8000
    SEARXNG_PORT: int = 8080
    CORS_ORIGINS: Annotated[tuple[str, ...], NoDecode] = (
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    )
    MAX_IMAGE_UPLOAD_BYTES: int = Field(default=10 * 1024 * 1024, ge=1_024)
    MAX_IMAGE_PIXELS: int = Field(default=20_000_000, ge=1_000_000)
    MAX_REMOTE_IMAGE_BYTES: int = Field(default=10 * 1024 * 1024, ge=1_024)
    MAX_SCRAPE_IMAGES: int = Field(default=100, ge=1, le=500)
    STRICT_REMOTE_URL_VALIDATION: bool = True

    # Paths
    STORAGE_DIR: str = os.path.join(os.getcwd(), "data")
    DB_PATH: str = os.path.join(os.getcwd(), "data", "facelens.db")
    INDEX_PATH: str = os.path.join(os.getcwd(), "data", "facelens.index")
    MODELS_DIR: str = os.path.expanduser("~/.insightface")

    # SearXNG configuration
    SEARXNG_URL: str = "http://localhost:8080"

    DISCLAIMER: str = (
        "La similarité faciale n'est pas une preuve d'identité. "
        "Vérifiez les sources avant toute conclusion."
    )

    @field_validator("FACELENS_API_KEY")
    @classmethod
    def validate_api_key(cls, value: str) -> str:
        key = value.strip()
        if len(key) < 32:
            raise ValueError("FACELENS_API_KEY doit contenir au moins 32 caractères.")
        return key

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: object) -> tuple[str, ...]:
        if isinstance(value, str):
            origins = tuple(origin.strip() for origin in value.split(",") if origin.strip())
        elif isinstance(value, (list, tuple, set)):
            origins = tuple(str(origin).strip() for origin in value if str(origin).strip())
        else:
            raise ValueError("CORS_ORIGINS doit être une liste ou une chaîne séparée par des virgules.")

        if not origins:
            raise ValueError("CORS_ORIGINS ne peut pas être vide.")
        if "*" in origins:
            raise ValueError("CORS_ORIGINS ne doit jamais contenir le joker '*'.")
        for origin in origins:
            parsed = urlparse(origin)
            if parsed.scheme not in {"http", "https"} or not parsed.netloc or parsed.path not in {"", "/"}:
                raise ValueError(f"Origine CORS invalide: {origin}")
        return origins

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )


settings = Settings()
os.makedirs(settings.STORAGE_DIR, exist_ok=True)
