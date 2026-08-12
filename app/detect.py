from typing import Any

from fastapi import APIRouter, File, HTTPException, UploadFile

from core.face_engine import get_face_engine
from core.security import read_validated_upload

router = APIRouter(tags=["Faces"])


def _serialize_face(face: Any) -> dict[str, Any]:
    return {
        "bbox": [round(float(value), 2) for value in face.bbox],
        "landmarks": [[round(float(x), 2), round(float(y), 2)] for x, y in face.kps],
        "det_score": round(float(face.det_score), 4),
    }


@router.post("/api/faces/detect")
async def detect_faces(file: UploadFile = File(...)) -> dict[str, Any]:
    """Return real InsightFace geometry for a validated image upload."""
    contents, _ = await read_validated_upload(file)
    engine = get_face_engine()
    try:
        image = engine.load_image(contents)
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    faces = engine._detect_faces_multiscale(image)
    serialized = [_serialize_face(face) for face in faces]
    return {"faces_detected": len(serialized), "faces": serialized}
