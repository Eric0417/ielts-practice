"""
FastAPI application entry point.

Starts up, registers all routers, configures CORS, and
triggers the content loader to sync meta.json files into the DB.
"""
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.database import engine
from app.models import Base
from app.routers import auth, questions, grading, attempts, admin
from app.routers import v2_content


# -------------------------------------------------------
# Lifespan — runs at startup and shutdown
# -------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: create tables (for dev convenience; production uses Alembic)
    Base.metadata.create_all(bind=engine, checkfirst=True)

    # Validate content directories exist (v2 PDF-driven system)
    from app.services.content_scanner import validate_content_dirs
    validate_content_dirs()

    yield
    # Shutdown: nothing to clean up for now


# -------------------------------------------------------
# Create the app
# -------------------------------------------------------
app = FastAPI(
    title="IELTS Practice API",
    description="Backend for the IELTS practice and grading platform",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS — allow frontend origins from config
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers
app.include_router(auth.router)
app.include_router(questions.router)
app.include_router(grading.router)
app.include_router(attempts.router)
app.include_router(admin.router)
app.include_router(v2_content.router)

# Serve content/ files (PDFs, MP3s) under /content/
content_dir = Path(__file__).resolve().parent.parent.parent / "content"
if content_dir.is_dir():
    app.mount("/content", StaticFiles(directory=str(content_dir)), name="content")
