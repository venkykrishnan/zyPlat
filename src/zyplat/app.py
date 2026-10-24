"""Application factory."""

from __future__ import annotations

from fastapi import FastAPI

from zyplat.api.domains import domains_router, instances_router
from zyplat.api.health import router as health_router
from zyplat.api.taxonomies import router as taxonomies_router
from zyplat.config import Settings
from zyplat.db import make_engine, make_session_factory
from zyplat.errors import register_exception_handlers
from zyplat.models import Base


def create_app(database_url: str | None = None) -> FastAPI:
    settings = Settings()
    url = settings.database_url if database_url is None else database_url
    engine = make_engine(url)
    Base.metadata.create_all(engine)
    app = FastAPI(
        title="Zyplat Taxonomy and Domain Service",
        version="0.1.0",
        description=(
            "Configure taxonomies and domains. Classifications are inherited down a "
            "hierarchy, and a domain instance admits base values plus values that carry "
            "one of its selected classifications."
        ),
    )
    app.state.engine = engine
    app.state.session_factory = make_session_factory(engine)
    register_exception_handlers(app)
    app.include_router(health_router)
    app.include_router(taxonomies_router, prefix="/api/v1")
    app.include_router(domains_router, prefix="/api/v1")
    app.include_router(instances_router, prefix="/api/v1")

    @app.get("/", include_in_schema=False)
    def root() -> dict[str, str]:
        return {"service": "zyplat", "docs": "/docs", "health": "/health"}

    return app
