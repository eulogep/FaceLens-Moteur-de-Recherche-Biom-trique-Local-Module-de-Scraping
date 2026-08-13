from typing import Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from app.routes.faces import get_db
from core.db import DatabaseManager

router = APIRouter(prefix="/api/faces", tags=["Faces"])


class FaceListItem(BaseModel):
    id: int
    image_path: str
    person_name: Optional[str] = None
    source_url: Optional[str] = None
    source_type: str
    tags: Optional[str] = ""
    created_at: str


class FaceListResponse(BaseModel):
    items: list[FaceListItem]
    total: int
    limit: int
    offset: int


class FaceCountResponse(BaseModel):
    total: int


def _image_reference(face_id: int) -> str:
    return f"/api/faces/{face_id}/image"


def _filters(source_type: str, query: str) -> tuple[list[str], list[str]]:
    clauses: list[str] = []
    parameters: list[str] = []
    if source_type:
        clauses.append("source_type = ?")
        parameters.append(source_type)
    if query:
        pattern = f"%{query}%"
        clauses.append(
            "("
            "person_name LIKE ? COLLATE NOCASE OR "
            "source_url LIKE ? COLLATE NOCASE OR "
            "tags LIKE ? COLLATE NOCASE OR "
            "CAST(id AS TEXT) LIKE ?"
            ")"
        )
        parameters.extend([pattern, pattern, pattern, pattern])
    return clauses, parameters


@router.get("", response_model=FaceListResponse)
async def list_faces(
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    source_type: str = Query(default=""),
    q: str = Query(default="", max_length=200),
    db: DatabaseManager = Depends(get_db),
) -> FaceListResponse:
    clauses, parameters = _filters(source_type.strip(), q.strip())
    where = f" WHERE {' AND '.join(clauses)}" if clauses else ""
    with db.get_connection() as connection:
        cursor = connection.cursor()
        cursor.execute(f"SELECT COUNT(*) FROM faces{where}", parameters)
        total = int(cursor.fetchone()[0])
        cursor.execute(
            "SELECT id, person_name, source_url, source_type, tags, created_at "
            f"FROM faces{where} ORDER BY created_at DESC, id DESC LIMIT ? OFFSET ?",
            [*parameters, limit, offset],
        )
        items = [
            FaceListItem(
                **dict(row),
                image_path=_image_reference(int(row["id"])),
            )
            for row in cursor.fetchall()
        ]
    return FaceListResponse(items=items, total=total, limit=limit, offset=offset)


@router.get("/count", response_model=FaceCountResponse)
async def count_faces(db: DatabaseManager = Depends(get_db)) -> FaceCountResponse:
    return FaceCountResponse(total=db.count_faces())
