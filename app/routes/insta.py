"""Additive Instagram public-ingestion routes."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, BackgroundTasks, Depends
from pydantic import BaseModel, Field, field_validator

from app.routes.faces import get_db, get_index
from core.config import settings
from core.db import DatabaseManager
from core.vector_index import VectorIndexManager
from spider.insta import InstagramIndexer

router = APIRouter(prefix="/api/insta", tags=["Instagram public"])


class InstagramProfileRequest(BaseModel):
    username: str = Field(min_length=1, max_length=31)

    @field_validator("username")
    @classmethod
    def normalize_username(cls, value: str) -> str:
        normalized = value.strip().lstrip("@")
        if not normalized or any(
            char not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._"
            for char in normalized
        ):
            raise ValueError("Nom d'utilisateur Instagram invalide.")
        return normalized


class InstagramMediasRequest(InstagramProfileRequest):
    amount: int = Field(default=10, ge=1, le=30)


class InstagramJobResponse(BaseModel):
    job_id: str
    status: str
    target_url: str
    mode: str
    disclaimer: str


@router.post("/profile", response_model=InstagramJobResponse)
async def index_public_profile(
    request: InstagramProfileRequest,
    background_tasks: BackgroundTasks,
    db: DatabaseManager = Depends(get_db),
    index: VectorIndexManager = Depends(get_index),
) -> dict[str, str]:
    """Queue anonymous indexing of an Instagram profile picture."""
    job_id = f"job_ig_profile_{uuid.uuid4().hex[:10]}"
    background_tasks.add_task(
        InstagramIndexer(db, index).execute_profile_job,
        job_id,
        request.username,
    )
    return {
        "job_id": job_id,
        "status": "pending",
        "target_url": f"instagram://profile/{request.username.lower()}",
        "mode": "public_anonymous",
        "disclaimer": settings.DISCLAIMER,
    }


@router.post("/medias", response_model=InstagramJobResponse)
async def index_public_medias(
    request: InstagramMediasRequest,
    background_tasks: BackgroundTasks,
    db: DatabaseManager = Depends(get_db),
    index: VectorIndexManager = Depends(get_index),
) -> dict[str, str]:
    """Queue anonymous indexing of recent public Instagram media."""
    job_id = f"job_ig_media_{uuid.uuid4().hex[:10]}"
    background_tasks.add_task(
        InstagramIndexer(db, index).execute_medias_job,
        job_id,
        request.username,
        request.amount,
    )
    return {
        "job_id": job_id,
        "status": "pending",
        "target_url": f"instagram://medias/{request.username.lower()}",
        "mode": "public_anonymous",
        "disclaimer": settings.DISCLAIMER,
    }
