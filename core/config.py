import os
from pydantic import AliasChoices, Field
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
    )  # CPU default (-1), set 0 for GPU
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

    # Thresholds for facial similarity (Cosine Similarity 0.0 to 1.0)
    THRESHOLD_STRONG: float = Field(
        default=0.70,
        validation_alias=AliasChoices("THRESHOLD_STRONG", "SIMILARITY_STRONG"),
    )
    THRESHOLD_MEDIUM: float = Field(
        default=0.50,
        validation_alias=AliasChoices("THRESHOLD_MEDIUM", "SIMILARITY_MEDIUM"),
    )
    THRESHOLD_LOOKALIKE: float = 0.50  # Below 0.50 is lookalike/false positive
    THRESHOLD_DEDUP: float = Field(
        default=0.95,
        validation_alias=AliasChoices("THRESHOLD_DEDUP", "DEDUP_THRESHOLD"),
    )  # For spider deduplication skip

    # Host ports (used by Docker Compose and available to local tooling)
    FACERLENS_PORT: int = 8000
    SEARXNG_PORT: int = 8080

    # Paths
    STORAGE_DIR: str = os.path.join(os.getcwd(), "data")
    DB_PATH: str = os.path.join(os.getcwd(), "data", "facelens.db")
    INDEX_PATH: str = os.path.join(os.getcwd(), "data", "facelens.index")
    # Note: InsightFace automatically appends 'models' to root, so root must be ~/.insightface
    MODELS_DIR: str = os.path.expanduser("~/.insightface")

    # SearXNG configuration (HTTP API, default localhost for host run, overridden in docker-compose)
    SEARXNG_URL: str = "http://localhost:8080"

    # Mandatory Legal / Ethical Warning
    DISCLAIMER: str = (
        "La similarité faciale n'est pas une preuve d'identité. "
        "Vérifiez les sources avant toute conclusion."
    )

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

settings = Settings()
os.makedirs(settings.STORAGE_DIR, exist_ok=True)
