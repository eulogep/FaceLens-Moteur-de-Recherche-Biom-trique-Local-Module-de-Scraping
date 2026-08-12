import logging
import mimetypes
import os
import uuid
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse

from app.schemas import (
    DeleteFaceResponse,
    EnrollResponse,
    FaceSearchResult,
    SearchResponse,
    VerifyResponse,
)
from core.config import settings
from core.db import DatabaseManager
from core.face_engine import get_face_engine
from core.security import read_validated_upload
from core.vector_index import VectorIndexManager

logger = logging.getLogger("facelens.routes.faces")
router = APIRouter(prefix="/api/faces", tags=["Faces"])

_db_manager: Optional[DatabaseManager] = None
_index_manager: Optional[VectorIndexManager] = None


def get_db() -> DatabaseManager:
    if _db_manager is None:
        raise HTTPException(status_code=500, detail="Database manager not initialized")
    return _db_manager


def get_index() -> VectorIndexManager:
    if _index_manager is None:
        raise HTTPException(status_code=500, detail="Index manager not initialized")
    return _index_manager


def configure_managers(db: DatabaseManager, index: VectorIndexManager) -> None:
    global _db_manager, _index_manager
    _db_manager = db
    _index_manager = index


def _image_directory() -> Path:
    directory = Path(settings.STORAGE_DIR, "images").resolve()
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def _safe_image_path(raw_path: str) -> Path | None:
    directory = _image_directory()
    candidate = Path(raw_path).resolve()
    try:
        candidate.relative_to(directory)
    except ValueError:
        return None
    return candidate


def _image_reference(face_id: int) -> str:
    return f"/api/faces/{face_id}/image"


@router.post("/verify", response_model=VerifyResponse)
async def verify_faces(image_a: UploadFile = File(...), image_b: UploadFile = File(...)):
    """Compare two validated image uploads without persisting either file."""
    bytes_a, _ = await read_validated_upload(image_a)
    bytes_b, _ = await read_validated_upload(image_b)
    return get_face_engine().verify_1v1(bytes_a, bytes_b)


@router.post("/enroll", response_model=EnrollResponse)
async def enroll_face(
    file: UploadFile = File(...),
    person_name: Optional[str] = Form(None),
    source_url: Optional[str] = Form(None),
    source_type: str = Form("local"),
    tags: str = Form(""),
    db: DatabaseManager = Depends(get_db),
    index: VectorIndexManager = Depends(get_index),
):
    """Enroll one validated face and retain only a local, non-public image file."""
    contents, extension = await read_validated_upload(file)
    engine = get_face_engine()
    faces = engine.extract_faces(contents)
    if not faces:
        raise HTTPException(status_code=400, detail="Aucun visage n'a été détecté dans l'image transmise.")

    top_face = max(faces, key=lambda face: face["det_score"])
    saved_path = _image_directory() / f"{uuid.uuid4().hex}{extension}"
    saved_path.write_bytes(contents)
    if not person_name and file.filename:
        base = os.path.splitext(file.filename)[0]
        if base and not base.isdigit() and len(base) > 2:
            person_name = base.replace("_", " ").replace("-", " ")
    try:
        enrolled = db.enroll_face_atomic(
            index_manager=index,
            vector=top_face["embedding"],
            image_path=str(saved_path),
            source_url=source_url,
            person_name=person_name,
            source_type=source_type,
            tags=tags,
            image_hash=top_face["phash"],
        )
    except Exception:
        saved_path.unlink(missing_ok=True)
        raise

    return {
        "id": enrolled["id"],
        "image_path": _image_reference(enrolled["id"]),
        "person_name": enrolled["person_name"],
        "source_url": enrolled["source_url"],
        "source_type": enrolled["source_type"],
        "tags": enrolled["tags"],
        "created_at": str(enrolled["created_at"]),
        "disclaimer": settings.DISCLAIMER,
    }


@router.get("/{face_id}/image")
async def get_face_image(face_id: int, db: DatabaseManager = Depends(get_db)) -> FileResponse:
    """Serve one corpus image only after global API-key authentication."""
    face = db.get_face(face_id)
    if not face:
        raise HTTPException(status_code=404, detail=f"Face ID #{face_id} introuvable.")
    image_path = _safe_image_path(face["image_path"])
    if image_path is None or not image_path.is_file():
        raise HTTPException(status_code=404, detail="Image biométrique indisponible.")
    media_type = mimetypes.guess_type(image_path.name)[0] or "application/octet-stream"
    return FileResponse(path=image_path, media_type=media_type, filename=image_path.name)


@router.post("/search", response_model=SearchResponse)
async def search_faces(
    file: UploadFile = File(...),
    top_k: int = Query(10, ge=1, le=100),
    min_similarity: float = Query(0.0, ge=0.0, le=1.0),
    db: DatabaseManager = Depends(get_db),
    index: VectorIndexManager = Depends(get_index),
):
    """Search a validated image against the local vector corpus."""
    contents, _ = await read_validated_upload(file)
    faces = get_face_engine().extract_faces(contents)
    if not faces:
        return {"faces_detected": 0, "results": [], "disclaimer": settings.DISCLAIMER}
    top_face = max(faces, key=lambda face: face["det_score"])
    raw_results = index.search(top_face["embedding"], top_k=top_k)
    if not raw_results:
        return {"faces_detected": len(faces), "results": [], "disclaimer": settings.DISCLAIMER}

    vector_ids = [result[0] for result in raw_results]
    sim_scores = {result[0]: result[1] for result in raw_results}
    search_results: list[FaceSearchResult] = []
    for record in db.get_faces_by_ids(vector_ids):
        face_id = record["id"]
        similarity = sim_scores.get(face_id, 0.0)
        if similarity < min_similarity:
            continue
        if similarity >= settings.THRESHOLD_STRONG:
            verdict = "fort"
        elif similarity >= settings.THRESHOLD_MEDIUM:
            verdict = "moyen"
        else:
            verdict = "sosie" if similarity >= settings.THRESHOLD_LOOKALIKE else "faux_positif"
        search_results.append(FaceSearchResult(
            id=face_id,
            similarity=round(similarity, 4),
            distance=round(1.0 - similarity, 4),
            verdict=verdict,
            image_path=_image_reference(face_id),
            person_name=record["person_name"],
            source_url=record["source_url"],
            source_type=record["source_type"],
            tags=record["tags"],
            created_at=str(record["created_at"]),
        ))
    search_results.sort(key=lambda result: result.similarity, reverse=True)
    return {"faces_detected": len(faces), "results": search_results, "disclaimer": settings.DISCLAIMER}


@router.delete("/{face_id}", response_model=DeleteFaceResponse)
async def delete_face(
    face_id: int,
    db: DatabaseManager = Depends(get_db),
    index: VectorIndexManager = Depends(get_index),
):
    """Delete a face from FAISS, SQLite and local biometric file storage."""
    face = db.get_face(face_id)
    if not face:
        raise HTTPException(status_code=404, detail=f"Face ID #{face_id} introuvable.")
    if not db.delete_face_atomic(index, face_id):
        raise HTTPException(status_code=404, detail=f"Face ID #{face_id} introuvable.")
    image_path = _safe_image_path(face["image_path"])
    if image_path is not None:
        try:
            image_path.unlink(missing_ok=True)
        except OSError as exc:
            logger.error("Unable to remove biometric image for face %s: %s", face_id, exc)
            raise HTTPException(status_code=500, detail="Le vecteur a été supprimé, mais le fichier biométrique doit être purgé manuellement.") from exc
    return {
        "success": True,
        "face_id": face_id,
        "message": f"Face #{face_id}, son vecteur et son fichier biométrique ont été supprimés.",
    }
