from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from app.config import settings
from app.database import SessionLocal, init_db
from app.ingestion.normalizer import get_city_data, get_featured_cities
from app.models import City
from app.routers import admin, cities, companies, jobs, search


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}…")
    init_db()
    _seed_cities()
    logger.info("Ready.")
    yield
    logger.info("Shutting down.")


def _seed_cities():
    """Populate the cities table from data/cities.json on every startup.
    Existing rows are left untouched; slug is unique so conflicts are skipped.
    """
    city_data = get_city_data()
    featured = set(get_featured_cities())
    db = SessionLocal()
    try:
        added = 0
        for name, info in city_data.items():
            slug = (
                name.lower()
                .replace(" ", "-")
                .replace("ã", "a")
                .replace("á", "a")
                .replace("â", "a")
                .replace("é", "e")
                .replace("ê", "e")
                .replace("í", "i")
                .replace("ó", "o")
                .replace("ô", "o")
                .replace("ú", "u")
                .replace("ü", "u")
                .replace("ç", "c")
            )
            if not db.query(City).filter(City.slug == slug).first():
                db.add(
                    City(
                        name=name,
                        slug=slug,
                        country=info["country"],
                        country_code=info["country_code"],
                        region=info.get("region", "").lower().replace(" ", "_") or None,
                        latitude=info["lat"],
                        longitude=info["lng"],
                        is_featured=name in featured,
                    )
                )
                added += 1
        db.commit()
        logger.info(f"Cities: {added} new rows added, table now ready")
    finally:
        db.close()


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=("JobDex startup job discovery API. Filter by city, role, and industry. "),
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
app.include_router(admin.router)


@app.get("/health", tags=["meta"])
def health():
    return {"status": "ok", "version": settings.APP_VERSION}


@app.get("/", tags=["meta"])
def root():
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "docs": "/docs",
        "primary_endpoint": "GET /search?city=&role=&industry=",
        "supported_ats": ["greenhouse", "lever", "ashby"],
        "endpoints": {
            "search": "GET  /search?city=&role=&industry=&country_code=&region=",
            "jobs": "GET  /jobs?city=&role_category=&seniority=&is_remote=",
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
