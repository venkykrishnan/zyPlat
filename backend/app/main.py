from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .core.config import settings
from .api import company, taxonomy, domain

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(company.router, prefix=f"{settings.API_V1_STR}/companies", tags=["companies"])
app.include_router(taxonomy.router, prefix=f"{settings.API_V1_STR}/taxonomies", tags=["taxonomies"])
app.include_router(domain.router, prefix=f"{settings.API_V1_STR}/domains", tags=["domains"])


@app.get("/health")
def health_check():
    return {"status": "healthy"}


@app.get("/")
def root():
    return {
        "name": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "docs": f"{settings.API_V1_STR}/docs",
    }
