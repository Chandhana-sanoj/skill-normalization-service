
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes.normalize import router as normalize_router
from app.repositories.canonical_skill_repository import (
    CanonicalSkillRepository,
)
from app.services.normalizer import SkillNormalizer
from app.services.vector_search import VectorSearcher


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Load the catalogue from PostgreSQL
    catalogue_repository = CanonicalSkillRepository()

    alias_map, canonical_map, description_map = (
        catalogue_repository.load_catalogue()
    )

    # Load the embedding model once
    vector_searcher = VectorSearcher()

    # Initialize the normalizer once
    app.state.normalizer = SkillNormalizer(
        alias_map=alias_map,
        canonical_map=canonical_map,
        vector_searcher=vector_searcher,
        organization_id=1,
        description_map=description_map,
    )

    yield


app = FastAPI(
    title="Skill Normalization Service",
    description="API for normalizing skill names and versions.",
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(normalize_router)


@app.get("/health")
def health_check():
    return {"status": "ok"}


