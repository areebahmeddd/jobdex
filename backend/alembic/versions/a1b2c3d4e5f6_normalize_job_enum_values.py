"""normalize job enum values

YCombinator wrote `fully_remote` and Teamtailor wrote `intern`, both off-vocabulary.
Fixed at the source, but dedup never rebuilds existing rows, so backfill them here.

Revision ID: a1b2c3d4e5f6
Revises: 60ea3f66d449
Create Date: 2026-09-10

"""

from collections.abc import Sequence

from alembic import op

revision: str = "a1b2c3d4e5f6"
down_revision: str | Sequence[str] | None = "60ea3f66d449"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Rewrite the off-vocabulary values to their canonical form."""
    op.execute("UPDATE jobs SET remote_type = 'fully-remote' WHERE remote_type = 'fully_remote'")
    op.execute("UPDATE jobs SET job_type = 'internship' WHERE job_type = 'intern'")


def downgrade() -> None:
    """No-op: the old values were spelling variants, not a distinct state."""
