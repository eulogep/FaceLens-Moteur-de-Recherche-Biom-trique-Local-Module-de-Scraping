import os
import uuid
import numpy as np
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Query, Depends
from typing import Optional, List

from core.config import settings
from core.face_engine import get_face_engine, FaceEngine
from core.vector_index import VectorIndexManager
from core.db import DatabaseManager
from app.schemas import (
    VerifyResponse, EnrollResponse, SearchResponse, FaceSearchResult, DeleteFaceResponse
)

router = APIRouter(prefix="/api/faces", tags=["Faces"])

# Dependencies provided at main startup
db_manager: Optional[DatabaseManager] = None
index_manager: Optional[VectorIndexManager] = None

def get_db() -> DatabaseManager:
    if db_manager is None:
        raise HTTPException(status_code=500, detail="Database manager not initialized")
    return db_manager

def get_index() -> VectorIndexManager:
    if index_manager is None:
        raise HTTPException(status_code=500, detail="Index manager not initialized")
    return index_manager

@router.post("/verify", response_model=VerifyResponse)
async def verify_faces(
    image_a: UploadFile = File(...),
    image_b: UploadFile = File(...)
):
    """
    1:1 Face Verification comparing two uploaded images.
    """
    engine = get_face_engine()
    bytes_a = await image_a.read()
    bytes_b = await image_b.read()
    
    result = engine.verify_1v1(bytes_a, bytes_b)
    return result

@router.post("/enroll", response_model=EnrollResponse)
async def enroll_face(
    file: UploadFile = File(...),
    person_name: Optional[str] = Form(None),
    source_url: Optional[str] = Form(None),
    source_type: str = Form("local"),
    tags: str = Form(""),
    db: DatabaseManager = Depends(get_db),
    index: VectorIndexManager = Depends(get_index)
):
    """
    Enroll a face into the corpus:
    1. Detect face & extract 512-d ArcFace vector.
    2. Save uploaded file to disk.
    3. Perform atomic insertion (SQLite first -> FAISS add_with_ids -> rollback if failure -> integrity check).
    """
    contents = await file.read()
    engine = get_face_engine()
    faces = engine.extract_faces(contents)

    if not faces:
        raise HTTPException(
            status_code=400,
            detail="Aucun visage n'a été détecté dans l'image transmise."
        )

    top_face = max(faces, key=lambda f: f["det_score"])
    vector = top_face["embedding"]
    phash = top_face["phash"]

    # Save image to storage directory
    ext = os.path.splitext(file.filename or "image.jpg")[1] or ".jpg"
    filename = f"{uuid.uuid4().hex}{ext}"
    images_dir = os.path.join(settings.STORAGE_DIR, "images")
    os.makedirs(images_dir, exist_ok=True)
    saved_path = os.path.join(images_dir, filename)

    with open(saved_path, "wb") as f:
        f.write(contents)

    # If person_name is missing, attempt to derive from original filename
    if not person_name and file.filename:
        base = os.path.splitext(file.filename)[0]
        if base and not base.isdigit() and len(base) > 2:
            person_name = base.replace("_", " ").replace("-", " ")

    enrolled = db.enroll_face_atomic(
        index_manager=index,
        vector=vector,
        image_path=saved_path,
        source_url=source_url,
        person_name=person_name,
        source_type=source_type,
        tags=tags,
        image_hash=phash
    )

    return {
        "id": enrolled["id"],
        "image_path": enrolled["image_path"],
        "person_name": enrolled["person_name"],
        "source_url": enrolled["source_url"],
        "source_type": enrolled["source_type"],
        "tags": enrolled["tags"],
        "created_at": str(enrolled["created_at"]),
        "disclaimer": settings.DISCLAIMER
    }

@router.post("/search", response_model=SearchResponse)
async def search_faces(
    file: UploadFile = File(...),
    top_k: int = Query(10, ge=1, le=100),
    min_similarity: float = Query(0.0, ge=0.0, le=1.0),
    db: DatabaseManager = Depends(get_db),
    index: VectorIndexManager = Depends(get_index)
):
    """
    1:N Face Search:
    Upload a photo, extract embedding, query FAISS index top-K, return matches sorted by similarity score.
    Thresholds:
    - >= 0.70 : Fort (Strong)
    - 0.50 - 0.70 : Moyen (Medium)
    - < 0.50 : Sosie / Faux Positif (Lookalike)
    """
    contents = await file.read()
    engine = get_face_engine()
    faces = engine.extract_faces(contents)

    if not faces:
        return {
            "faces_detected": 0,
            "results": [],
            "disclaimer": settings.DISCLAIMER
        }

    top_face = max(faces, key=lambda f: f["det_score"])
    query_vector = top_face["embedding"]

    # FAISS search
    raw_results = index.search(query_vector, top_k=top_k)
    if not raw_results:
        return {
            "faces_detected": len(faces),
            "results": [],
            "disclaimer": settings.DISCLAIMER
        }

    vector_ids = [res[0] for res in raw_results]
    sim_scores = {res[0]: res[1] for res in raw_results}

    # Fetch corresponding DB metadata
    db_records = db.get_faces_by_ids(vector_ids)

    search_results = []
    for rec in db_records:
        fid = rec["id"]
        sim = sim_scores.get(fid, 0.0)
        if sim < min_similarity:
            continue
        dist = 1.0 - sim

        if sim >= settings.THRESHOLD_STRONG:
            verdict = "fort"
        elif sim >= settings.THRESHOLD_MEDIUM:
            verdict = "moyen"
        else:
            verdict = "sosie" if sim >= settings.THRESHOLD_LOOKALIKE else "faux_positif"

        search_results.append(FaceSearchResult(
            id=rec["id"],
            similarity=round(sim, 4),
            distance=round(dist, 4),
            verdict=verdict,
            image_path=rec["image_path"],
            person_name=rec["person_name"],
            source_url=rec["source_url"],
            source_type=rec["source_type"],
            tags=rec["tags"],
            created_at=str(rec["created_at"])
        ))

    # Sort descending by similarity
    search_results.sort(key=lambda r: r.similarity, reverse=True)

    return {
        "faces_detected": len(faces),
        "results": search_results,
        "disclaimer": settings.DISCLAIMER
    }

@router.delete("/{face_id}", response_model=DeleteFaceResponse)
async def delete_face(
    face_id: int,
    db: DatabaseManager = Depends(get_db),
    index: VectorIndexManager = Depends(get_index)
):
    """
    Delete a face from FAISS vector index and SQLite metadata (Right to be forgotten).
    FAISS deletion happens first, then SQLite deletion.
    """
    success = db.delete_face_atomic(index, face_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"Face ID #{face_id} untrouvable.")

    return {
        "success": True,
        "face_id": face_id,
        "message": f"Face #{face_id} et son vecteur ont été supprimés avec succès."
    }
