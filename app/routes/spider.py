import uuid
from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from typing import Dict, Any

from core.db import DatabaseManager
from core.vector_index import VectorIndexManager
from app.routes.faces import get_db, get_index
from app.schemas import (
    ScrapeUrlRequest, ScrapeProfileRequest, ScrapeSearchRequest,
    ScrapeJobResponse, ScrapeJobStatusResponse, DeleteFaceResponse,
    DeleteDomainResponse, SystemStatsResponse
)
from spider.job_manager import ScrapeJobManager

router = APIRouter(prefix="/api/scrape", tags=["Spider / Scraping"])

@router.post("/url", response_model=ScrapeJobResponse)
async def scrape_url(
    req: ScrapeUrlRequest,
    background_tasks: BackgroundTasks,
    db: DatabaseManager = Depends(get_db),
    index: VectorIndexManager = Depends(get_index)
):
    """
    Queue a public URL scraping job to extract and index faces.
    """
    job_id = f"job_{uuid.uuid4().hex[:12]}"
    job_manager = ScrapeJobManager(db, index)

    background_tasks.add_task(
        job_manager.execute_url_job,
        job_id=job_id,
        url=req.url,
        max_images=req.max_images,
        source_type=req.source_type,
        dry_run=req.dry_run
    )

    return {
        "job_id": job_id,
        "status": "pending",
        "target_url": req.url
    }

@router.get("/status/{job_id}", response_model=ScrapeJobStatusResponse)
async def get_scrape_status(
    job_id: str,
    db: DatabaseManager = Depends(get_db)
):
    """
    Get scraping job progress, faces indexed, duplicates skipped, and errors_by_domain.
    """
    job = db.get_scrape_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job #{job_id} introuvable.")

    return {
        "job_id": job["job_id"],
        "target_url": job["target_url"],
        "status": job["status"],
        "total_images": job["total_images"],
        "faces_indexed": job["faces_indexed"],
        "duplicates_skipped": job["duplicates_skipped"],
        "errors_by_domain": job.get("errors_by_domain", {}),
        "created_at": str(job["created_at"]),
        "updated_at": str(job["updated_at"])
    }

@router.post("/profile", response_model=ScrapeJobResponse)
async def scrape_profile(
    req: ScrapeProfileRequest,
    background_tasks: BackgroundTasks,
    db: DatabaseManager = Depends(get_db),
    index: VectorIndexManager = Depends(get_index)
):
    """
    Scrape public social/forum profile page.
    """
    # Construct target profile URL
    target_url = f"https://{req.platform}.com/{req.username}"
    job_id = f"job_prof_{uuid.uuid4().hex[:10]}"
    job_manager = ScrapeJobManager(db, index)

    background_tasks.add_task(
        job_manager.execute_url_job,
        job_id=job_id,
        url=target_url,
        max_images=req.max_images,
        source_type=req.platform,
        dry_run=req.dry_run
    )

    return {
        "job_id": job_id,
        "status": "pending",
        "target_url": target_url
    }

@router.post("/search", response_model=ScrapeJobResponse)
async def scrape_search(
    req: ScrapeSearchRequest,
    background_tasks: BackgroundTasks,
    db: DatabaseManager = Depends(get_db),
    index: VectorIndexManager = Depends(get_index)
):
    """
    Execute a SearXNG image search query, retrieve result image links, and index faces.
    """
    job_id = f"job_sx_{uuid.uuid4().hex[:10]}"
    job_manager = ScrapeJobManager(db, index)

    background_tasks.add_task(
        job_manager.execute_searxng_job,
        job_id=job_id,
        query=req.query,
        limit=req.limit,
        dry_run=req.dry_run
    )

    return {
        "job_id": job_id,
        "status": "pending",
        "target_url": f"searxng://{req.query}"
    }

@router.delete("/face/{face_id}", response_model=DeleteFaceResponse)
async def delete_scrape_face(
    face_id: int,
    db: DatabaseManager = Depends(get_db),
    index: VectorIndexManager = Depends(get_index)
):
    """
    Right to be forgotten: Delete scraped face vector and metadata by face ID.
    """
    success = db.delete_face_atomic(index, face_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"Face ID #{face_id} untrouvable.")

    return {
        "success": True,
        "face_id": face_id,
        "message": f"Face #{face_id} et son vecteur ont été supprimés de l'index."
    }

@router.delete("/source/{domain}", response_model=DeleteDomainResponse)
async def delete_source_domain(
    domain: str,
    db: DatabaseManager = Depends(get_db),
    index: VectorIndexManager = Depends(get_index)
):
    """
    Blacklist an entire domain and purge all associated face entries from the index.
    """
    deleted_count = db.delete_domain_atomic(index, domain)
    return {
        "domain": domain,
        "deleted_faces_count": deleted_count,
        "message": f"Le domaine '{domain}' a été exclu et {deleted_count} visage(s) associés ont été purgés."
    }

@router.get("/stats", response_model=SystemStatsResponse)
async def get_system_stats(
    db: DatabaseManager = Depends(get_db),
    index: VectorIndexManager = Depends(get_index)
):
    """
    Returns system statistics and verifies atomic SQLite <-> FAISS integrity.
    """
    stats = db.get_scrape_stats()
    integrity_ok = db.verify_integrity(index)

    return {
        "total_jobs": stats["total_jobs"],
        "scraped_faces": stats["scraped_faces"],
        "excluded_domains_count": stats["excluded_domains_count"],
        "faces_by_source_type": stats["faces_by_source_type"],
        "total_indexed_faces": stats["total_indexed_faces"],
        "faiss_ntotal": index.ntotal,
        "integrity_verified": integrity_ok
    }
