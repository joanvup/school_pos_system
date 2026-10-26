"""Operaciones de Fase 3: importaciones persistentes y límites de solicitudes.

Revision ID: 0003_phase3_ops
Revises: 0002_auth_hardening
Create Date: 2026-10-26
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "0003_phase3_ops"
down_revision: Union[str, None] = "0002_auth_hardening"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

NOW = sa.text("CURRENT_TIMESTAMP")


def upgrade() -> None:
    op.create_table(
        "import_jobs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("kind", sa.String(length=20), nullable=False),
        sa.Column(
            "status", sa.String(length=20), server_default="processing", nullable=False
        ),
        sa.Column("progress", sa.Integer(), server_default="0", nullable=False),
        sa.Column("result", sa.JSON(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=NOW, nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=NOW, nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        mysql_charset="utf8mb4",
    )
    op.create_index("ix_import_jobs_user_id", "import_jobs", ["user_id"])
    op.create_index(
        "ix_import_jobs_user_created", "import_jobs", ["user_id", "created_at"]
    )

    op.create_table(
        "request_throttles",
        sa.Column("key", sa.String(length=160), nullable=False),
        sa.Column("window_start", sa.DateTime(), nullable=False),
        sa.Column("count", sa.Integer(), server_default="0", nullable=False),
        sa.PrimaryKeyConstraint("key"),
        mysql_charset="utf8mb4",
    )
    op.create_index(
        "ix_request_throttles_window_start", "request_throttles", ["window_start"]
    )


def downgrade() -> None:
    op.drop_index(
        "ix_request_throttles_window_start", table_name="request_throttles"
    )
    op.drop_table("request_throttles")
    op.drop_index("ix_import_jobs_user_created", table_name="import_jobs")
    op.drop_index("ix_import_jobs_user_id", table_name="import_jobs")
    op.drop_table("import_jobs")
