"""Esquema inicial de School POS (Fase 1).

Revision ID: 0001_initial
Revises:
Create Date: 2026-10-26

Notas:
- Todo el dinero usa NUMERIC(12, 2).
- Los CHECK se agregan solo en MySQL >= 8.0.16; en versiones anteriores
  la aplicación valida las mismas reglas.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


MONEY = sa.Numeric(12, 2)
NOW = sa.text("CURRENT_TIMESTAMP")


def _supports_check_constraints() -> bool:
    bind = op.get_bind()
    if bind.dialect.name != "mysql":
        return True
    version = bind.dialect.server_version_info or ()
    return version >= (8, 0, 16)


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("full_name", sa.String(length=150), nullable=False),
        sa.Column("email", sa.String(length=100), nullable=False),
        sa.Column("hashed_password", sa.String(length=255), nullable=False),
        sa.Column(
            "role",
            sa.Enum(
                "ADMIN",
                "SUPERVISOR",
                "VENDEDOR",
                "PADRE",
                "EMPLEADO",
                name="userrole",
            ),
            nullable=True,
        ),
        sa.Column("is_active", sa.Boolean(), nullable=True),
        sa.Column("must_change_password", sa.Boolean(), nullable=False),
        sa.Column("token_version", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=NOW, nullable=True),
        sa.Column("pending_balance", MONEY, nullable=False),
        sa.PrimaryKeyConstraint("id"),
        mysql_charset="utf8mb4",
    )
    op.create_index("ix_users_id", "users", ["id"])
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "categories",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        mysql_charset="utf8mb4",
    )
    op.create_index("ix_categories_id", "categories", ["id"])
    op.create_index("ix_categories_name", "categories", ["name"], unique=True)

    op.create_table(
        "products",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("description", sa.String(length=255), nullable=True),
        sa.Column("category_id", sa.Integer(), nullable=False),
        sa.Column("price", MONEY, nullable=False),
        sa.Column("cost", MONEY, nullable=False),
        sa.Column("stock", sa.Integer(), nullable=False),
        sa.Column("low_stock_threshold", sa.Integer(), nullable=True),
        sa.Column("image_url", sa.String(length=255), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["category_id"], ["categories.id"]),
        sa.PrimaryKeyConstraint("id"),
        mysql_charset="utf8mb4",
    )
    op.create_index("ix_products_id", "products", ["id"])
    op.create_index("ix_products_name", "products", ["name"])

    op.create_table(
        "students",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("full_name", sa.String(length=150), nullable=False),
        sa.Column("grade", sa.String(length=50), nullable=True),
        sa.Column("parent_id", sa.Integer(), nullable=True),
        sa.Column("pending_balance", MONEY, nullable=False),
        sa.ForeignKeyConstraint(["parent_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        mysql_charset="utf8mb4",
    )
    op.create_index("ix_students_id", "students", ["id"])

    op.create_table(
        "cards",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("uid", sa.String(length=50), nullable=False),
        sa.Column("balance", MONEY, nullable=False),
        sa.Column(
            "status",
            sa.Enum("ACTIVE", "BLOCKED", name="cardstatus"),
            nullable=False,
        ),
        sa.Column("daily_limit", MONEY, nullable=True),
        sa.Column("student_id", sa.Integer(), nullable=True),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["student_id"], ["students.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("student_id", name="uq_cards_student_id"),
        sa.UniqueConstraint("user_id", name="uq_cards_user_id"),
        mysql_charset="utf8mb4",
    )
    op.create_index("ix_cards_id", "cards", ["id"])
    op.create_index("ix_cards_uid", "cards", ["uid"], unique=True)

    op.create_table(
        "transactions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("card_id", sa.Integer(), nullable=False),
        sa.Column("amount", MONEY, nullable=False),
        sa.Column(
            "type",
            sa.Enum("RECHARGE", "PURCHASE", name="transactiontype"),
            nullable=False,
        ),
        sa.Column("description", sa.String(length=255), nullable=True),
        sa.Column("timestamp", sa.DateTime(timezone=True), server_default=NOW, nullable=True),
        sa.Column("reference_code", sa.String(length=64), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("cus", sa.String(length=100), nullable=True),
        sa.Column("gateway", sa.String(length=30), nullable=True),
        sa.Column("currency", sa.String(length=10), nullable=True),
        sa.Column("payment_method", sa.String(length=30), nullable=True),
        sa.Column("raw_notification", sa.Text(), nullable=True),
        sa.Column("response_code", sa.String(length=100), nullable=True),
        sa.Column("credited_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reversed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reversed_by_id", sa.Integer(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=NOW, nullable=True),
        sa.ForeignKeyConstraint(["card_id"], ["cards.id"]),
        sa.ForeignKeyConstraint(["reversed_by_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        mysql_charset="utf8mb4",
    )
    op.create_index("ix_transactions_id", "transactions", ["id"])
    op.create_index("ix_transactions_card_id", "transactions", ["card_id"])
    op.create_index("ix_transactions_timestamp", "transactions", ["timestamp"])
    op.create_index(
        "ix_transactions_reference_code", "transactions", ["reference_code"], unique=True
    )
    op.create_index("ix_transactions_cus", "transactions", ["cus"])
    op.create_index("ix_transactions_gateway", "transactions", ["gateway"])
    op.create_index(
        "ix_transactions_card_timestamp", "transactions", ["card_id", "timestamp"]
    )
    op.create_index(
        "ix_transactions_status_type", "transactions", ["status", "type"]
    )
    op.create_index(
        "ix_transactions_gateway_reference", "transactions", ["gateway", "reference_code"]
    )

    op.create_table(
        "transaction_details",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("transaction_id", sa.Integer(), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=True),
        sa.Column("product_name", sa.String(length=100), nullable=True),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("unit_price", MONEY, nullable=False),
        sa.Column("subtotal", MONEY, nullable=False),
        sa.ForeignKeyConstraint(["transaction_id"], ["transactions.id"]),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"]),
        sa.PrimaryKeyConstraint("id"),
        mysql_charset="utf8mb4",
    )
    op.create_index("ix_transaction_details_id", "transaction_details", ["id"])
    op.create_index(
        "ix_transaction_details_transaction_id", "transaction_details", ["transaction_id"]
    )

    op.create_table(
        "payment_notifications",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("reference_code", sa.String(length=64), nullable=True),
        sa.Column("gateway", sa.String(length=30), nullable=False),
        sa.Column("raw", sa.Text(), nullable=True),
        sa.Column("remote_ip", sa.String(length=45), nullable=True),
        sa.Column("signature_valid", sa.Boolean(), nullable=False),
        sa.Column("reason", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=NOW, nullable=True),
        sa.PrimaryKeyConstraint("id"),
        mysql_charset="utf8mb4",
    )
    op.create_index("ix_payment_notifications_id", "payment_notifications", ["id"])
    op.create_index(
        "ix_payment_notifications_reference_code",
        "payment_notifications",
        ["reference_code"],
    )
    op.create_index(
        "ix_payment_notifications_created_at", "payment_notifications", ["created_at"]
    )

    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("action", sa.String(length=50), nullable=False),
        sa.Column("entity", sa.String(length=30), nullable=True),
        sa.Column("entity_id", sa.Integer(), nullable=True),
        sa.Column("details", sa.Text(), nullable=True),
        sa.Column("ip", sa.String(length=45), nullable=True),
        sa.Column("timestamp", sa.DateTime(timezone=True), server_default=NOW, nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        mysql_charset="utf8mb4",
    )
    op.create_index("ix_audit_logs_id", "audit_logs", ["id"])
    op.create_index("ix_audit_logs_user_id", "audit_logs", ["user_id"])
    op.create_index("ix_audit_logs_action", "audit_logs", ["action"])
    op.create_index("ix_audit_logs_timestamp", "audit_logs", ["timestamp"])

    op.create_table(
        "purchase_orders",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("code", sa.String(length=50), nullable=True),
        sa.Column("timestamp", sa.DateTime(timezone=True), server_default=NOW, nullable=True),
        sa.Column(
            "status",
            sa.Enum("COMPLETED", "CANCELLED", name="orderstatus"),
            nullable=True,
        ),
        sa.Column("total_cost", MONEY, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        mysql_charset="utf8mb4",
    )
    op.create_index("ix_purchase_orders_id", "purchase_orders", ["id"])
    op.create_index("ix_purchase_orders_code", "purchase_orders", ["code"], unique=True)

    op.create_table(
        "purchase_order_details",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("order_id", sa.Integer(), nullable=True),
        sa.Column("product_id", sa.Integer(), nullable=True),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("unit_cost", MONEY, nullable=False),
        sa.ForeignKeyConstraint(["order_id"], ["purchase_orders.id"]),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"]),
        sa.PrimaryKeyConstraint("id"),
        mysql_charset="utf8mb4",
    )
    op.create_index("ix_purchase_order_details_id", "purchase_order_details", ["id"])

    op.create_table(
        "stock_adjustments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("code", sa.String(length=50), nullable=True),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), server_default=NOW, nullable=True),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        mysql_charset="utf8mb4",
    )
    op.create_index("ix_stock_adjustments_id", "stock_adjustments", ["id"])
    op.create_index(
        "ix_stock_adjustments_code", "stock_adjustments", ["code"], unique=True
    )

    op.create_table(
        "stock_adjustment_details",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("adjustment_id", sa.Integer(), nullable=True),
        sa.Column("product_id", sa.Integer(), nullable=True),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["adjustment_id"], ["stock_adjustments.id"]),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"]),
        sa.PrimaryKeyConstraint("id"),
        mysql_charset="utf8mb4",
    )
    op.create_index("ix_stock_adjustment_details_id", "stock_adjustment_details", ["id"])

    op.create_table(
        "system_settings",
        sa.Column("key", sa.String(length=50), nullable=False),
        sa.Column("value", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("key"),
        mysql_charset="utf8mb4",
    )
    op.create_index("ix_system_settings_key", "system_settings", ["key"])

    op.create_table(
        "payment_gateway_settings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("gateway", sa.String(length=30), nullable=False),
        sa.Column("label", sa.String(length=80), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=True),
        sa.Column("is_test", sa.Boolean(), nullable=True),
        sa.Column("has_credentials", sa.Boolean(), nullable=True),
        sa.Column("config", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        mysql_charset="utf8mb4",
    )
    op.create_index("ix_payment_gateway_settings_id", "payment_gateway_settings", ["id"])
    op.create_index(
        "ix_payment_gateway_settings_gateway",
        "payment_gateway_settings",
        ["gateway"],
        unique=True,
    )

    if _supports_check_constraints():
        op.create_check_constraint("ck_users_pending_balance_non_negative", "users", "pending_balance >= 0")
        op.create_check_constraint("ck_users_token_version_non_negative", "users", "token_version >= 0")
        op.create_check_constraint("ck_students_pending_balance_non_negative", "students", "pending_balance >= 0")
        op.create_check_constraint("ck_products_price_non_negative", "products", "price >= 0")
        op.create_check_constraint("ck_products_cost_non_negative", "products", "cost >= 0")
        op.create_check_constraint("ck_products_stock_non_negative", "products", "stock >= 0")
        op.create_check_constraint("ck_products_low_stock_threshold_non_negative", "products", "low_stock_threshold >= 0")
        op.create_check_constraint("ck_cards_balance_non_negative", "cards", "balance >= 0")
        op.create_check_constraint("ck_cards_daily_limit_non_negative", "cards", "daily_limit IS NULL OR daily_limit >= 0")
        op.create_check_constraint("ck_transactions_amount_non_zero", "transactions", "amount <> 0")
        op.create_check_constraint("ck_transaction_details_quantity_positive", "transaction_details", "quantity > 0")
        op.create_check_constraint("ck_transaction_details_price_non_negative", "transaction_details", "unit_price >= 0")
        op.create_check_constraint("ck_transaction_details_subtotal_non_negative", "transaction_details", "subtotal >= 0")
        op.create_check_constraint("ck_purchase_details_quantity_positive", "purchase_order_details", "quantity > 0")
        op.create_check_constraint("ck_purchase_details_unit_cost_non_negative", "purchase_order_details", "unit_cost >= 0")


def downgrade() -> None:
    op.drop_table("payment_gateway_settings")
    op.drop_table("system_settings")
    op.drop_table("stock_adjustment_details")
    op.drop_table("stock_adjustments")
    op.drop_table("purchase_order_details")
    op.drop_table("purchase_orders")
    op.drop_table("audit_logs")
    op.drop_table("payment_notifications")
    op.drop_table("transaction_details")
    op.drop_table("transactions")
    op.drop_table("cards")
    op.drop_table("students")
    op.drop_table("products")
    op.drop_table("categories")
    op.drop_table("users")
