"""FastAPI application entry point for the NexGen retail assistant."""

import logging
import time
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from backend.app.config import settings
from backend.app.db import init_db_pool, close_db_pool
from backend.app.rag.embeddings import initialize_embedding_client
from backend.app.api.routes_tools import router as tools_router
from backend.app.api.routes_meta import router as meta_router
from backend.app.api.routes_orchestrator import router as orchestrator_router
from backend.app.api.routes_voice import router as voice_router
from backend.app.api.routes_catalogue import router as catalogue_router
from backend.app.api.routes_retell import router as retell_router
from backend.app.api.routes_admin import router as admin_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("tool_gateway.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle managing database connection pool."""
    logger.info("Starting %s (Environment: %s)...", settings.app_name, settings.environment)
    init_db_pool()
    embedding_started = time.perf_counter()
    embedding_client = initialize_embedding_client()
    logger.info("Embedding model initialized at startup: provider=%s model=%s device=%s elapsed_ms=%.2f",
                embedding_client.provider, embedding_client.model,
                getattr(embedding_client, "device", "remote"),
                (time.perf_counter() - embedding_started) * 1000)
    warmup_started = time.perf_counter()
    embedding_client.embed(["NexGen voice commerce startup warmup"])
    logger.info("Embedding model warmed at startup: elapsed_ms=%.2f",
                (time.perf_counter() - warmup_started) * 1000)
    yield
    logger.info("Shutting down %s...", settings.app_name)
    close_db_pool()


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Deterministic backend for the NexGen retail voice commerce assistant.",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount Routers
app.include_router(meta_router)
app.include_router(tools_router)
app.include_router(orchestrator_router)
app.include_router(voice_router)
app.include_router(catalogue_router)
app.include_router(retell_router)
app.include_router(admin_router)


@app.get("/")
def root_index():
    return {
        "gateway": settings.app_name,
        "version": settings.app_version,
        "status": "operational",
        "docs": "/docs",
        "health": "/health",
        "tool_definitions": "/v1/tools/definitions",
        "public_catalogue": "/v1/catalogue/products"
    }
