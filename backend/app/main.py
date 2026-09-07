"""FastAPI Application Entry Point for Zara AI Tool Gateway."""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from backend.app.config import settings
from backend.app.db import init_db_pool, close_db_pool
from backend.app.api.routes_tools import router as tools_router
from backend.app.api.routes_meta import router as meta_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("tool_gateway.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle managing database connection pool."""
    logger.info("Starting Zara AI Tool Gateway (Environment: %s)...", settings.environment)
    init_db_pool()
    yield
    logger.info("Shutting down Zara AI Tool Gateway...")
    close_db_pool()


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Deterministic AI Tool Gateway providing safe, controlled business operations over the Zara retail dataset.",
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


@app.get("/")
def root_index():
    return {
        "gateway": settings.app_name,
        "version": settings.app_version,
        "status": "operational",
        "docs": "/docs",
        "health": "/health",
        "tool_definitions": "/v1/tools/definitions"
    }
