from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from app.config import settings
from app.database import init_db
from app.routers import admin, cities, companies, jobs, map, search
from app.startup import seed_cities


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize the database and seed cities on startup, then shut down cleanly."""
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}...")
    init_db()
    seed_cities()
    logger.info("Ready.")
    yield
    logger.info("Shutting down.")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=settings.APP_DESCRIPTION,
    debug=settings.DEBUG,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(jobs.router)
app.include_router(companies.router)
app.include_router(search.router)
app.include_router(cities.router)
app.include_router(map.router)
app.include_router(admin.router)


@app.get("/health", tags=["meta"])
def health():
    """Return service health status and current version."""
    return {"status": "ok", "version": settings.APP_VERSION}


@app.get("/", tags=["meta"])
def root():
    """Return API metadata, supported ATS providers, and primary endpoints."""
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "docs": "/docs",
        "primary_endpoint": "GET /map/companies  (globe render)",
        "supported_ats": ["greenhouse", "lever", "ashby"],
        "endpoints": {
            "map": {
                "companies": "GET  /map/companies?region=&role=&lat_min=&lat_max=&lng_min=&lng_max=",
                "cities": "GET  /map/cities?region=&role=&featured_only=true",
            },
            "search": "GET  /search?city=&role=&industry=&country_code=&region=",
            "jobs": "GET  /jobs?city=&role_category=&seniority=&is_remote=&q=&cursor=",
            "companies": "GET  /companies?city=&industry=&country_code=&region=",
            "cities": "GET  /cities?region=&featured_only=true",
            "stats": "GET  /stats",
            "ingest": {
                "greenhouse": "POST /ingest/greenhouse/{slug}",
                "lever": "POST /ingest/lever/{slug}",
                "ashby": "POST /ingest/ashby/{slug}",
                "discover": "POST /ingest/discover/{slug}  (auto-detect ATS)",
            },
        },
    }
