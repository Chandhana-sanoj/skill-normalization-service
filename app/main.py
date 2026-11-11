
from contextlib import asynccontextmanager
import os

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.api.routes.catalog import router as catalog_router

from fastapi.middleware.cors import CORSMiddleware
from app.core.config import CORS_ORIGINS

from app.api.routes.super_admin_auth import router as super_admin_auth_router
from app.api.routes.super_admin import router as super_admin_router

from app.api.routes.users import router as users_router

from app.api.routes.normalize import router as normalize_router
from app.api.routes.auth import router as auth_router
from app.api.routes.organizations import router as organizations_router
from app.api.routes.unresolved import router as unresolved_router
from app.api.routes.history import router as history_router
from app.repositories.canonical_skill_repository import (
    CanonicalSkillRepository,
)
from app.services.vector_search import VectorSearcher


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load catalogue data and initialize services at application startup."""
    catalogue_repository = CanonicalSkillRepository()

    (
        alias_map,
        canonical_map,
        description_map,
        category_map,
        aliases_by_canonical,
    ) = catalogue_repository.load_catalogue()

    vector_searcher = VectorSearcher()

    app.state.alias_map = alias_map
    app.state.canonical_map = canonical_map
    app.state.description_map = description_map
    app.state.category_map = category_map
    app.state.aliases_by_canonical = aliases_by_canonical
    app.state.vector_searcher = vector_searcher

    yield


app = FastAPI(
    title="Skill Normalization Service",
    description="API for normalizing skill names and versions.",
    version="1.0.0",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(normalize_router)
app.include_router(auth_router)
app.include_router(organizations_router)
app.include_router(unresolved_router)
app.include_router(history_router)
app.include_router(catalog_router)
app.include_router(users_router)
app.include_router(super_admin_auth_router)
app.include_router(super_admin_router)
@app.get("/health")
def health_check():
    """Check whether the API is running."""
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# Production SPA static-file serving
# ---------------------------------------------------------------------------
# When the unified frontend is built (`cd frontend && npm run build`), it
# outputs to frontend/dist/.  In production (or local `uvicorn app.main:app`)
# FastAPI serves those files so both the org app and the Super Admin app are
# accessible from one origin, with no separate static server needed.
#
# Mount order matters: /api routes must be registered first (above) so they
# are matched before the catch-all SPA fallback below.
#
# In development, Vite's dev server (port 5173) proxies /api to FastAPI, so
# this block is harmlessly skipped (dist/ does not exist yet).
# ---------------------------------------------------------------------------
_DIST_DIR = os.path.join(os.path.dirname(__file__), "..", "frontend", "dist")

if os.path.isdir(_DIST_DIR):
    # Serve static assets (JS / CSS / images) from dist/assets/
    _ASSETS_DIR = os.path.join(_DIST_DIR, "assets")
    if os.path.isdir(_ASSETS_DIR):
        app.mount("/assets", StaticFiles(directory=_ASSETS_DIR), name="spa-assets")

    # SPA catch-all: serve index.html for every non-API path so that
    # React's client-side router (hash-based for SA, state-based for org)
    # handles navigation after the initial page load.
    @app.get("/{full_path:path}", include_in_schema=False)
    def serve_spa(full_path: str):
        """Serve the unified React SPA for all non-API routes."""
        index = os.path.join(_DIST_DIR, "index.html")
        return FileResponse(index)
