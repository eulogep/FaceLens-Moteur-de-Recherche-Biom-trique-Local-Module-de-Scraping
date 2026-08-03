import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from core.config import settings
from core.db import DatabaseManager
from core.vector_index import VectorIndexManager
from core.face_engine import get_face_engine
import app.routes.faces as faces_module
import app.routes.spider as spider_module
from app.routes.faces import router as faces_router
from app.routes.spider import router as spider_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup initialization
    db = DatabaseManager(settings.DB_PATH)
    index = VectorIndexManager(dimension=512, index_path=settings.INDEX_PATH)
    
    # Verify atomic consistency at boot
    db.verify_integrity(index)
    
    # Warm up face engine model
    get_face_engine()

    # Pass managers to routes
    faces_module.db_manager = db
    faces_module.index_manager = index
    spider_module.db_manager = db
    spider_module.index_manager = index

    yield

    # Shutdown handler: Save FAISS index
    if faces_module.index_manager:
        faces_module.index_manager.save()

app = FastAPI(
    title="FaceLens API",
    description="Engine de recherche de visages biométriques local & self-hosted avec scraping automatisé.",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve uploaded / scraped images statically
images_dir = os.path.join(settings.STORAGE_DIR, "images")
os.makedirs(images_dir, exist_ok=True)
app.mount("/static/images", StaticFiles(directory=images_dir), name="static_images")

# Mount API routers
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
        "docs_url": "/docs"
    }
