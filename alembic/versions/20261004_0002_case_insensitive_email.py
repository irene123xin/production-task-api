"""Enforce case-insensitive email uniqueness."""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20261004_0002"
down_revision: str | None = "20261004_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_index("ix_users_email", table_name="users")
    op.create_index("uq_users_email_normalized", "users", [sa.text("lower(email)")], unique=True)


def downgrade() -> None:
    op.drop_index("uq_users_email_normalized", table_name="users")
    op.create_index("ix_users_email", "users", ["email"], unique=True)
