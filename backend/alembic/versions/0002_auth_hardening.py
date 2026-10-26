"""Endurecimiento de autenticación (Fase 2).

Revision ID: 0002_auth_hardening
Revises: 0001_initial
Create Date: 2026-10-26
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "0002_auth_hardening"
down_revision: Union[str, None] = "0001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

NOW = sa.text("CURRENT_TIMESTAMP")


def _supports_check_constraints() -> bool:
    bind = op.get_bind()
    if bind.dialect.name != "mysql":
        return True
    return (bind.dialect.server_version_info or ()) >= (8, 0, 16)


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "failed_login_attempts",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    )
    op.add_column("users", sa.Column("locked_until", sa.DateTime(), nullable=True))

    op.create_table(
        "password_reset_tokens",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("purpose", sa.String(length=32), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("used_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=NOW, nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        mysql_charset="utf8mb4",
    )
    op.create_index(
        "ix_password_reset_tokens_id", "password_reset_tokens", ["id"]
    )
    op.create_index(
        "ix_password_reset_tokens_user_id",
        "password_reset_tokens",
        ["user_id"],
    )
    op.create_index(
        "ix_password_reset_tokens_token_hash",
        "password_reset_tokens",
        ["token_hash"],
        unique=True,
    )
    op.create_index(
        "ix_password_reset_user_created",
        "password_reset_tokens",
        ["user_id", "created_at"],
    )

    if _supports_check_constraints():
        op.create_check_constraint(
            "ck_users_failed_login_attempts_non_negative",
            "users",
            "failed_login_attempts >= 0",
        )


def downgrade() -> None:
    if _supports_check_constraints():
        op.drop_constraint(
            "ck_users_failed_login_attempts_non_negative",
            "users",
            type_="check",
        )
    op.drop_index(
        "ix_password_reset_user_created", table_name="password_reset_tokens"
    )
    op.drop_index(
        "ix_password_reset_tokens_token_hash", table_name="password_reset_tokens"
    )
    op.drop_index(
        "ix_password_reset_tokens_user_id", table_name="password_reset_tokens"
    )
    op.drop_index("ix_password_reset_tokens_id", table_name="password_reset_tokens")
    op.drop_table("password_reset_tokens")
    op.drop_column("users", "locked_until")
    op.drop_column("users", "failed_login_attempts")
