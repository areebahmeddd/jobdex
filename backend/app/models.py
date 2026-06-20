import uuid
from datetime import UTC, datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Company(Base):
    __tablename__ = "companies"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    logo_url: Mapped[str | None] = mapped_column(String(500))
    description: Mapped[str | None] = mapped_column(Text)
    website: Mapped[str | None] = mapped_column(String(500))

    city: Mapped[str | None] = mapped_column(String(255), index=True)
    country: Mapped[str | None] = mapped_column(String(255))
    country_code: Mapped[str | None] = mapped_column(String(2), index=True)
    region: Mapped[str | None] = mapped_column(String(50))
    latitude: Mapped[float | None] = mapped_column(Float)
    longitude: Mapped[float | None] = mapped_column(Float)

    industry: Mapped[list[str] | None] = mapped_column(JSONB, default=list)
    stage: Mapped[str | None] = mapped_column(String(50))
    founded_year: Mapped[int | None] = mapped_column(Integer)

    ats_type: Mapped[str | None] = mapped_column(String(50))
    ats_slug: Mapped[str | None] = mapped_column(String(255))
    last_crawled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    crawl_error: Mapped[str | None] = mapped_column(String(500))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    wikidata_id: Mapped[str | None] = mapped_column(String(20))
    enriched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    founders: Mapped[list | None] = mapped_column(JSONB)
    key_investors: Mapped[list | None] = mapped_column(JSONB)
    total_funding_usd: Mapped[int | None] = mapped_column(BigInteger)
    funding_stage: Mapped[str | None] = mapped_column(String(50))
    business_model: Mapped[str | None] = mapped_column(String(50))
    headcount_range: Mapped[str | None] = mapped_column(String(50))
    benefits: Mapped[list | None] = mapped_column(JSONB)
    office_address: Mapped[str | None] = mapped_column(String(500))
    social_links: Mapped[dict | None] = mapped_column(JSONB)

    jobs: Mapped[list["Job"]] = relationship("Job", back_populates="company", lazy="select")

    __table_args__ = (
        Index("ix_companies_city_country", "city", "country_code"),
        Index("ix_companies_region", "region"),
        Index("ix_companies_industry_gin", "industry", postgresql_using="gin"),
    )


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    company_id: Mapped[str] = mapped_column(String, ForeignKey("companies.id"), nullable=False)

    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    description_snippet: Mapped[str | None] = mapped_column(String(600))

    location_raw: Mapped[str | None] = mapped_column(String(500))
    city: Mapped[str | None] = mapped_column(String(255), index=True)
    country: Mapped[str | None] = mapped_column(String(255))
    country_code: Mapped[str | None] = mapped_column(String(2), index=True)
    region: Mapped[str | None] = mapped_column(String(50))
    latitude: Mapped[float | None] = mapped_column(Float)
    longitude: Mapped[float | None] = mapped_column(Float)
    is_remote: Mapped[bool] = mapped_column(Boolean, default=False)
    remote_type: Mapped[str | None] = mapped_column(String(50))

    role_category: Mapped[str | None] = mapped_column(String(100), index=True)
    role_subcategory: Mapped[str | None] = mapped_column(String(100))
    seniority: Mapped[str | None] = mapped_column(String(50), index=True)
    job_type: Mapped[str | None] = mapped_column(String(50))
    department: Mapped[str | None] = mapped_column(String(255))
    tech_stack: Mapped[list[str] | None] = mapped_column(JSONB, default=list)

    source_url: Mapped[str] = mapped_column(String(1000), nullable=False)
    ats_type: Mapped[str | None] = mapped_column(String(50))
    ats_job_id: Mapped[str | None] = mapped_column(String(255))
    dedup_hash: Mapped[str | None] = mapped_column(String(64), unique=True, index=True)

    posted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    first_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)

    company: Mapped["Company"] = relationship("Company", back_populates="jobs")

    __table_args__ = (
        Index("ix_jobs_company_active", "company_id", "is_active"),
        Index(
            "ix_jobs_fts_gin",
            text(
                "to_tsvector('english',"
                " coalesce(title,'') || ' ' ||"
                " coalesce(description_snippet,'') || ' ' ||"
                " coalesce(role_category,''))"
            ),
            postgresql_using="gin",
            postgresql_where=text("is_active = TRUE"),
        ),
        Index(
            "ix_jobs_active_city_role",
            "city",
            "role_category",
            postgresql_where=text("is_active = TRUE"),
        ),
        Index(
            "ix_jobs_active_region_role",
            "region",
            "role_category",
            postgresql_where=text("is_active = TRUE"),
        ),
        Index(
            "ix_jobs_active_country_role",
            "country_code",
            "role_category",
            postgresql_where=text("is_active = TRUE"),
        ),
        Index(
            "ix_jobs_active_posted",
            "posted_at",
            postgresql_where=text("is_active = TRUE"),
        ),
    )


class City(Base):
    __tablename__ = "cities"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    country: Mapped[str | None] = mapped_column(String(255))
    country_code: Mapped[str | None] = mapped_column(String(2))
    region: Mapped[str | None] = mapped_column(String(50))
    latitude: Mapped[float | None] = mapped_column(Float)
    longitude: Mapped[float | None] = mapped_column(Float)
