from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.routes.faces import get_db
from core.db import DatabaseManager


router = APIRouter(prefix="/api/scrape", tags=["Spider / Scraping"])


class ExcludedDomain(BaseModel):
    domain: str
    created_at: str


class ExcludedDomainListResponse(BaseModel):
    domains: list[ExcludedDomain]
    total: int


@router.get("/domains", response_model=ExcludedDomainListResponse)
async def list_excluded_domains(
    db: DatabaseManager = Depends(get_db),
) -> ExcludedDomainListResponse:
    with db.get_connection() as connection:
        cursor = connection.cursor()
        cursor.execute(
            "SELECT domain, created_at FROM excluded_domains "
            "ORDER BY created_at DESC, domain ASC"
        )
        domains = [ExcludedDomain(**dict(row)) for row in cursor.fetchall()]

    return ExcludedDomainListResponse(domains=domains, total=len(domains))
