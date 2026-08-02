from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

class VerifyResponse(BaseModel):
    verified: bool
    similarity: float
    distance: float
    threshold: float
    verdict: str
    warning: Optional[str] = None
    disclaimer: str

class FaceMetadata(BaseModel):
    id: int
    image_path: str
    source_url: Optional[str] = None
    person_name: Optional[str] = None
    source_type: str = "local"
    tags: Optional[str] = ""
    created_at: str

class EnrollResponse(BaseModel):
    id: int
    image_path: str
    person_name: Optional[str] = None
    source_url: Optional[str] = None
    source_type: str = "local"
    tags: Optional[str] = ""
    created_at: str
    disclaimer: str

class FaceSearchResult(BaseModel):
    id: int
    similarity: float
    distance: float
    verdict: str  # fort / moyen / sosie / faux_positif
    image_path: str
    person_name: Optional[str] = None
    source_url: Optional[str] = None
    source_type: str = "local"
    tags: Optional[str] = ""
    created_at: str

class SearchResponse(BaseModel):
    faces_detected: int
    results: List[FaceSearchResult]
    disclaimer: str

class ScrapeUrlRequest(BaseModel):
    url: str
    max_images: int = Field(default=50, ge=1, le=500)
    source_type: str = "web"
    dry_run: bool = False

class ScrapeProfileRequest(BaseModel):
    platform: str
    username: str
    max_images: int = Field(default=50, ge=1, le=500)
    dry_run: bool = False

class ScrapeSearchRequest(BaseModel):
    query: str
    engine: str = "searxng"
    limit: int = Field(default=20, ge=1, le=100)
    dry_run: bool = False

class ScrapeJobResponse(BaseModel):
    job_id: str
    status: str
    target_url: str

class ScrapeJobStatusResponse(BaseModel):
    job_id: str
    target_url: str
    status: str
    total_images: int
    faces_indexed: int
    duplicates_skipped: int
    errors_by_domain: Dict[str, str] = Field(default_factory=dict)
    created_at: str
    updated_at: str

class DeleteFaceResponse(BaseModel):
    success: bool
    face_id: int
    message: str

class DeleteDomainResponse(BaseModel):
    domain: str
    deleted_faces_count: int
    message: str

class SystemStatsResponse(BaseModel):
    total_jobs: int
    scraped_faces: int
    excluded_domains_count: int
    faces_by_source_type: Dict[str, int]
    total_indexed_faces: int
    faiss_ntotal: int
    integrity_verified: bool
