from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from core.config import settings
from core.db import DatabaseManager
from core.face_engine import get_face_engine
from core.vector_index import VectorIndexManager

import app.routes.faces as faces_module
import app.routes.spider as spider_module
from app.routes.faces import router as faces_router
from app.routes.spider import router as spider_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialise les dépendances locales et vérifie l’intégrité du corpus."""
    db = DatabaseManager(settings.DB_PATH)
    index = VectorIndexManager(dimension=512, index_path=settings.INDEX_PATH)
    db.verify_integrity(index)
    get_face_engine()

    faces_module.db_manager = db
    faces_module.index_manager = index
    spider_module.db_manager = db
    spider_module.index_manager = index
    yield

    if faces_module.index_manager:
        faces_module.index_manager.save()


app = FastAPI(
    title="FaceLens API",
    description="Moteur local de similarité faciale avec garde-fous de collecte et de stockage.",
    version="1.1.0",
    lifespan=lifespan,
)

# The corpus is sensitive. Browser requests are limited to explicit local
# frontend origins; credentials are not enabled with wildcard origins.
app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.CORS_ORIGINS),
    allow_credentials=False,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["Content-Type"],
    max_age=600,
)

app.include_router(faces_router)
app.include_router(spider_router)
app.include_router(__import__("app.detect", fromlist=["router"]).router)
app.include_router(__import__("app.faces_list", fromlist=["router"]).router)
app.include_router(__import__("app.domains_list", fromlist=["router"]).router)
app.include_router(__import__("app.routes.insta", fromlist=["router"]).router)


@app.get("/")
async def root():
    return {
        "app": "FaceLens",
        "status": "online",
        "disclaimer": settings.DISCLAIMER,
        "docs_url": "/docs",
    }
