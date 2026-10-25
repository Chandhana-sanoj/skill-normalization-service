
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes.catalog import router as catalog_router

from fastapi.middleware.cors import CORSMiddleware
from app.core.config import CORS_ORIGINS

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
    ) = catalogue_repository.load_catalogue()

    vector_searcher = VectorSearcher()

    app.state.alias_map = alias_map
    app.state.canonical_map = canonical_map
    app.state.description_map = description_map
    app.state.category_map = category_map
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


@app.get("/health")
def health_check():
    """Check whether the API is running."""
    return {"status": "ok"}
