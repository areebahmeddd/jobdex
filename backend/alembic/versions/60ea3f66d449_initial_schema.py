"""initial schema

Revision ID: 60ea3f66d449
Revises:
Create Date: 2026-06-20

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "60ea3f66d449"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create initial schema: companies, cities, and jobs tables with all indexes."""
    op.create_table(
        "companies",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(255), nullable=False),
        sa.Column("logo_url", sa.String(500), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("website", sa.String(500), nullable=True),
        sa.Column("city", sa.String(255), nullable=True),
        sa.Column("country", sa.String(255), nullable=True),
        sa.Column("country_code", sa.String(2), nullable=True),
        sa.Column("region", sa.String(50), nullable=True),
        sa.Column("latitude", sa.Float(), nullable=True),
        sa.Column("longitude", sa.Float(), nullable=True),
        sa.Column("industry", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("stage", sa.String(50), nullable=True),
        sa.Column("founded_year", sa.Integer(), nullable=True),
        sa.Column("ats_type", sa.String(50), nullable=True),
        sa.Column("ats_slug", sa.String(255), nullable=True),
        sa.Column("last_crawled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("crawl_error", sa.String(500), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("wikidata_id", sa.String(20), nullable=True),
        sa.Column("enriched_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("founders", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("key_investors", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("total_funding_usd", sa.BigInteger(), nullable=True),
        sa.Column("funding_stage", sa.String(50), nullable=True),
        sa.Column("business_model", sa.String(50), nullable=True),
        sa.Column("headcount_range", sa.String(50), nullable=True),
        sa.Column("benefits", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("office_address", sa.String(500), nullable=True),
        sa.Column("social_links", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug"),
    )
    op.create_index("ix_companies_slug", "companies", ["slug"], unique=True)
    op.create_index("ix_companies_city", "companies", ["city"])
    op.create_index("ix_companies_country_code", "companies", ["country_code"])
    op.create_index("ix_companies_city_country", "companies", ["city", "country_code"])
    op.create_index("ix_companies_region", "companies", ["region"])
    op.create_index("ix_companies_industry_gin", "companies", ["industry"], postgresql_using="gin")

    op.create_table(
        "cities",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(255), nullable=False),
        sa.Column("country", sa.String(255), nullable=True),
        sa.Column("country_code", sa.String(2), nullable=True),
        sa.Column("region", sa.String(50), nullable=True),
        sa.Column("latitude", sa.Float(), nullable=True),
        sa.Column("longitude", sa.Float(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug"),
    )
    op.create_index("ix_cities_slug", "cities", ["slug"], unique=True)

    op.create_table(
        "jobs",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("company_id", sa.String(), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("description_snippet", sa.String(600), nullable=True),
        sa.Column("location_raw", sa.String(500), nullable=True),
        sa.Column("city", sa.String(255), nullable=True),
        sa.Column("country", sa.String(255), nullable=True),
        sa.Column("country_code", sa.String(2), nullable=True),
        sa.Column("region", sa.String(50), nullable=True),
        sa.Column("latitude", sa.Float(), nullable=True),
        sa.Column("longitude", sa.Float(), nullable=True),
        sa.Column("is_remote", sa.Boolean(), nullable=False),
        sa.Column("remote_type", sa.String(50), nullable=True),
        sa.Column("role_category", sa.String(100), nullable=True),
        sa.Column("role_subcategory", sa.String(100), nullable=True),
        sa.Column("seniority", sa.String(50), nullable=True),
        sa.Column("job_type", sa.String(50), nullable=True),
        sa.Column("department", sa.String(255), nullable=True),
        sa.Column("tech_stack", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("source_url", sa.String(1000), nullable=False),
        sa.Column("ats_type", sa.String(50), nullable=True),
        sa.Column("ats_job_id", sa.String(255), nullable=True),
        sa.Column("dedup_hash", sa.String(64), nullable=True),
        sa.Column("posted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("dedup_hash"),
    )
    op.create_index("ix_jobs_city", "jobs", ["city"])
    op.create_index("ix_jobs_country_code", "jobs", ["country_code"])
    op.create_index("ix_jobs_role_category", "jobs", ["role_category"])
    op.create_index("ix_jobs_seniority", "jobs", ["seniority"])
    op.create_index("ix_jobs_dedup_hash", "jobs", ["dedup_hash"], unique=True)
    op.create_index("ix_jobs_is_active", "jobs", ["is_active"])
    op.create_index("ix_jobs_company_active", "jobs", ["company_id", "is_active"])
    op.create_index(
        "ix_jobs_fts_gin",
        "jobs",
        [
            sa.literal_column(
                "to_tsvector('english',"
                " coalesce(title,'') || ' ' ||"
                " coalesce(description_snippet,'') || ' ' ||"
                " coalesce(role_category,''))"
            )
        ],
        postgresql_using="gin",
        postgresql_where=sa.text("is_active = TRUE"),
    )
    op.create_index(
        "ix_jobs_active_city_role",
        "jobs",
        ["city", "role_category"],
        postgresql_where=sa.text("is_active = TRUE"),
    )
    op.create_index(
        "ix_jobs_active_region_role",
        "jobs",
        ["region", "role_category"],
        postgresql_where=sa.text("is_active = TRUE"),
    )
    op.create_index(
        "ix_jobs_active_country_role",
        "jobs",
        ["country_code", "role_category"],
        postgresql_where=sa.text("is_active = TRUE"),
    )
    op.create_index(
        "ix_jobs_active_posted",
        "jobs",
        ["posted_at"],
        postgresql_where=sa.text("is_active = TRUE"),
    )


def downgrade() -> None:
    """Drop all tables in dependency order."""
    op.drop_table("jobs")
    op.drop_table("cities")
    op.drop_table("companies")
