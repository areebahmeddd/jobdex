import uuid
from datetime import UTC, datetime

from sqlalchemy import (
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
    description: Mapped[str | None] = mapped_column(Text)
    website: Mapped[str | None] = mapped_column(String(500))

    city: Mapped[str | None] = mapped_column(String(255), index=True)
    country: Mapped[str | None] = mapped_column(String(255))
    country_code: Mapped[str | None] = mapped_column(String(2), index=True)
    latitude: Mapped[float | None] = mapped_column(Float)
    longitude: Mapped[float | None] = mapped_column(Float)
    region: Mapped[str | None] = mapped_column(String(50))

    industry: Mapped[list | None] = mapped_column(JSONB, default=list)
    stage: Mapped[str | None] = mapped_column(String(50))
    founded_year: Mapped[int | None] = mapped_column(Integer)
    employee_count_range: Mapped[str | None] = mapped_column(String(50))

    ats_type: Mapped[str | None] = mapped_column(String(50))  # greenhouse | lever | ashby
    ats_slug: Mapped[str | None] = mapped_column(String(255))

    logo_url: Mapped[str | None] = mapped_column(String(500))
    last_crawled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    crawl_error: Mapped[str | None] = mapped_column(String(500))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )

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
    title_normalized: Mapped[str | None] = mapped_column(String(500))
    description: Mapped[str | None] = mapped_column(Text)
    description_snippet: Mapped[str | None] = mapped_column(String(600))

    location_raw: Mapped[str | None] = mapped_column(String(500))
    city: Mapped[str | None] = mapped_column(String(255), index=True)
    country: Mapped[str | None] = mapped_column(String(255))
    country_code: Mapped[str | None] = mapped_column(String(2), index=True)
    latitude: Mapped[float | None] = mapped_column(Float)
    longitude: Mapped[float | None] = mapped_column(Float)
    region: Mapped[str | None] = mapped_column(String(50))
    is_remote: Mapped[bool] = mapped_column(Boolean, default=False)
    remote_type: Mapped[str | None] = mapped_column(String(50))  # fully-remote | hybrid | onsite

    job_type: Mapped[str | None] = mapped_column(String(50))
    seniority: Mapped[str | None] = mapped_column(String(50), index=True)
    role_category: Mapped[str | None] = mapped_column(String(100), index=True)
    role_subcategory: Mapped[str | None] = mapped_column(String(100))
    tech_stack: Mapped[list | None] = mapped_column(JSONB, default=list)
    department: Mapped[str | None] = mapped_column(String(255))

    salary_min: Mapped[int | None] = mapped_column(Integer)
    salary_max: Mapped[int | None] = mapped_column(Integer)
    salary_currency: Mapped[str | None] = mapped_column(String(3))

    source_url: Mapped[str] = mapped_column(String(1000), nullable=False)
    ats_type: Mapped[str | None] = mapped_column(String(50))
    ats_job_id: Mapped[str | None] = mapped_column(String(255))
    dedup_hash: Mapped[str | None] = mapped_column(String(64), unique=True, index=True)

    posted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    first_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )

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
    description: Mapped[str | None] = mapped_column(Text)
    is_featured: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
