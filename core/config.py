import os
from pydantic import AliasChoices, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


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

    # Runtime and network limits
    FACELENS_PORT: int = 8000
    SEARXNG_PORT: int = 8080
    CORS_ORIGINS: tuple[str, ...] = (
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

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: object) -> tuple[str, ...]:
        if isinstance(value, str):
            return tuple(origin.strip() for origin in value.split(",") if origin.strip())
        if isinstance(value, (list, tuple, set)):
            return tuple(str(origin).strip() for origin in value if str(origin).strip())
        raise ValueError("CORS_ORIGINS doit être une liste ou une chaîne séparée par des virgules.")

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )


settings = Settings()
os.makedirs(settings.STORAGE_DIR, exist_ok=True)
