"""FastAPI Main Application"""
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.utils.config import settings
from app.dependencies import get_db, get_current_user, engine
from app.api import auth, documents, queries, batch, admin, folders, policy


# Lifespan manager
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    from app.models.base import Base
    import app.models.user
    import app.models.document
    import app.models.query
    import app.models.document  # Import again to ensure Folder model is registered

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    print(f"Starting {settings.app_name} v{settings.app_version}")
    yield
    # Shutdown
    print("Shutting down application")


# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Multi-user RAG platform with dynamic workflow selection",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(documents.router, prefix="/api/documents", tags=["Documents"])
app.include_router(queries.router, prefix="/api/queries", tags=["Queries"])
app.include_router(batch.router, prefix="/api/batch", tags=["Batch Processing"])
app.include_router(admin.router, prefix="/api/admin", tags=["Admin"])
app.include_router(folders.router, prefix="/api/folders", tags=["Folders"])
app.include_router(policy.router, prefix="/api/policy", tags=["Policy"])


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "app_name": settings.app_name,
        "version": settings.app_version
    }


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": f"Welcome to {settings.app_name}",
        "version": settings.app_version,
        "docs": "/docs"
    }
