from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from app import scheduler as _scheduler
from app.config import settings
from app.database import migrate_db
from app.routers import cities, companies, jobs, map, payments, search, stats
from app.startup import seed_cities


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize the database, seed cities, and start the scheduler on startup."""
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}...")
    migrate_db()
    seed_cities()
    _scheduler.start()
    logger.info("Ready.")
    yield
    _scheduler.stop()
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
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)

app.include_router(jobs.router)
app.include_router(companies.router)
app.include_router(cities.router)
app.include_router(search.router)
app.include_router(map.router)
app.include_router(stats.router)
app.include_router(payments.router)


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
        "supported_ats": ["ashby", "greenhouse", "lever", "ycombinator"],
        "endpoints": {
            "jobs": "GET /jobs?city=&role_category=&seniority=&is_remote=&q=&cursor=",
            "companies": "GET /companies?city=&industry=&country_code=&region=",
            "cities": "GET /cities?region=&country_code=",
            "search": "GET /search?city=&role=&industry=&country_code=&region=",
            "map": {
                "companies": "GET /map/companies?region=&role=&lat_min=&lat_max=&lng_min=&lng_max=",
                "cities": "GET /map/cities?region=&role=&is_remote=",
            },
            "stats": "GET /stats",
        },
    }
