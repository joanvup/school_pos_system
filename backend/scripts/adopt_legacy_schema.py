"""Adopta una base legacy al esquema Alembic actual sin perder datos.

La base legacy tiene el dinero en FLOAT, no conoce Alembic y le faltan
columnas, índices, CHECK constraints y las tablas de Fase 1/2. Este script
la lleva a paridad con la revisión `0002_auth_hardening`:

- Convierte columnas monetarias a DECIMAL(12,2).
- Agrega columnas, índices, llaves foráneas y CHECK constraints.
- Crea `payment_notifications` y `password_reset_tokens`.
- Rellena `credited_at` de recargas aprobadas (idempotencia de PayU).
- Deja solo PayU en `payment_gateway_settings`.

No borra filas de negocio. No ejecuta el cifrado de `smtp_pass`: eso lo hace
`python -m app.db.init_db` después, con SETTINGS_ENCRYPTION_KEY definida.

Uso:
    python -m scripts.adopt_legacy_schema --check
    ALLOW_LEGACY_MIGRATION=true python -m scripts.adopt_legacy_schema --apply

Antes de --apply debe existir un backup verificado. Si algo falla, la única
vuelta atrás es restaurar ese backup.
"""

import argparse
import hashlib
import json
import os
import sys
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path

from sqlalchemy import text

from app.db.session import engine

MONEY = "DECIMAL(12,2)"
HEAD_REVISION = "0002_auth_hardening"

# Columnas que deben sobrevivir intactas (se excluyen las nuevas y las que se
# normalizan a propósito). El hash detecta cualquier pérdida o cambio de fila.
SNAPSHOT_TABLES = {
    "users": (
        [
            "id",
            "email",
            "full_name",
            "role",
            "is_active",
            "hashed_password",
            "created_at",
            "pending_balance",
        ],
        {"pending_balance"},
    ),
    "students": (
        ["id", "full_name", "grade", "parent_id", "pending_balance"],
        {"pending_balance"},
    ),
    "cards": (
        ["id", "uid", "balance", "status", "daily_limit", "student_id", "user_id"],
        {"balance", "daily_limit"},
    ),
    "products": (
        [
            "id",
            "name",
            "description",
            "category_id",
            "price",
            "cost",
            "stock",
            "low_stock_threshold",
            "image_url",
            "is_active",
            "updated_at",
        ],
        {"price", "cost"},
    ),
    "categories": (["id", "name"], set()),
    "transactions": (
        [
            "id",
            "card_id",
            "amount",
            "type",
            "description",
            "timestamp",
            "reference_code",
            "cus",
            "status",
            "gateway",
            "currency",
            "payment_method",
            "raw_notification",
            "response_code",
        ],
        {"amount"},
    ),
    "transaction_details": (
        [
            "id",
            "transaction_id",
            "product_id",
            "product_name",
            "quantity",
            "unit_price",
            "subtotal",
        ],
        {"unit_price", "subtotal"},
    ),
    "audit_logs": (["id", "user_id", "action", "details", "timestamp"], set()),
    "purchase_orders": (
        ["id", "code", "timestamp", "status", "total_cost", "user_id"],
        {"total_cost"},
    ),
    "purchase_order_details": (
        ["id", "order_id", "product_id", "quantity", "unit_cost"],
        {"unit_cost"},
    ),
    "stock_adjustments": (["id", "code", "reason", "timestamp", "user_id"], set()),
    "stock_adjustment_details": (
        ["id", "adjustment_id", "product_id", "quantity"],
        set(),
    ),
    "system_settings": (["key", "value"], set()),
}


def _norm(value, money: bool = False) -> str:
    if value is None:
        return "<NULL>"
    if money:
        try:
            return f"{Decimal(str(value)).quantize(Decimal('0.01'))}"
        except (InvalidOperation, ValueError):
            return f"<INVALID:{value}>"
    if isinstance(value, (datetime, date)):
        return value.isoformat(sep=" ")
    if isinstance(value, bytes):
        return value.hex()
    if isinstance(value, bool):
        return "1" if value else "0"
    return str(value)


def snapshot(conn) -> dict:
    data = {}
    for table, (cols, money_cols) in SNAPSHOT_TABLES.items():
        # CAST evita que FLOAT se lea redondeado a 6 dígitos significativos.
        select_cols = ", ".join(
            (
                f"CAST(`{c}` AS DECIMAL(20,4))"
                if c in money_cols
                else f"`{c}`"
            )
            for c in cols
        )
        rows = conn.execute(text(f"SELECT {select_cols} FROM `{table}`")).all()
        normalized = sorted(
            tuple(_norm(value, col in money_cols) for col, value in zip(cols, row))
            for row in rows
        )
        digest = hashlib.sha256(repr(normalized).encode("utf-8")).hexdigest()
        data[table] = {"rows": len(rows), "sha256": digest}
    return data


def _scalar(conn, sql: str, **params):
    return conn.execute(text(sql), params).scalar()


def _table_exists(conn, table: str) -> bool:
    return bool(
        _scalar(
            conn,
            "SELECT COUNT(*) FROM information_schema.tables "
            "WHERE table_schema = DATABASE() AND table_name = :t",
            t=table,
        )
    )


def _column(conn, table: str, name: str):
    return conn.execute(
        text(
            "SELECT COLUMN_TYPE, IS_NULLABLE, COLUMN_DEFAULT "
            "FROM information_schema.columns "
            "WHERE table_schema = DATABASE() AND table_name = :t "
            "AND column_name = :c"
        ),
        {"t": table, "c": name},
    ).first()


def _index_exists(conn, table: str, name: str) -> bool:
    return bool(
        _scalar(
            conn,
            "SELECT COUNT(*) FROM information_schema.statistics "
            "WHERE table_schema = DATABASE() AND table_name = :t AND index_name = :n",
            t=table,
            n=name,
        )
    )


def _check_exists(conn, table: str, name: str) -> bool:
    return bool(
        _scalar(
            conn,
            "SELECT COUNT(*) FROM information_schema.table_constraints "
            "WHERE constraint_schema = DATABASE() AND table_name = :t "
            "AND constraint_name = :n AND constraint_type = 'CHECK'",
            t=table,
            n=name,
        )
    )


def _fk_on_column_exists(conn, table: str, column: str) -> bool:
    return bool(
        _scalar(
            conn,
            "SELECT COUNT(*) FROM information_schema.key_column_usage "
            "WHERE table_schema = DATABASE() AND table_name = :t "
            "AND column_name = :c AND referenced_table_name IS NOT NULL",
            t=table,
            c=column,
        )
    )


def _check_constraints_supported(conn) -> bool:
    version = conn.engine.dialect.server_version_info or ()
    return version >= (8, 0, 16)


class Migrator:
    def __init__(self, conn):
        self.conn = conn
        self.applied: list[str] = []

    def _exec(self, sql: str) -> None:
        print(f"[DDL ] {sql}")
        self.conn.execute(text(sql))
        self.conn.commit()
        self.applied.append(sql)

    def add_column(self, table: str, name: str, ddl: str) -> None:
        if _column(self.conn, table, name) is None:
            self._exec(f"ALTER TABLE `{table}` ADD COLUMN `{name}` {ddl}")

    def modify_column(
        self, table: str, name: str, ddl_type: str, nullable: bool
    ) -> None:
        info = _column(self.conn, table, name)
        if info is None:
            raise RuntimeError(f"Falta la columna {table}.{name}")
        current_type = (info[0] or "").lower().replace(" ", "")
        current_null = info[1] == "YES"
        desired_type = ddl_type.lower().replace(" ", "")
        if current_type == desired_type and current_null == nullable:
            return
        null_sql = "NULL" if nullable else "NOT NULL"
        self._exec(f"ALTER TABLE `{table}` MODIFY COLUMN `{name}` {ddl_type} {null_sql}")

    def drop_default(self, table: str, name: str) -> None:
        info = _column(self.conn, table, name)
        if info is not None and info[2] is not None:
            self._exec(f"ALTER TABLE `{table}` ALTER COLUMN `{name}` DROP DEFAULT")

    def normalize_now_default(self, table: str, name: str) -> None:
        info = _column(self.conn, table, name)
        if info is None:
            return
        default = (info[2] or "").lower()
        if default in {"now()", "current_timestamp", "current_timestamp()"} and default != "current_timestamp":
            self._exec(
                f"ALTER TABLE `{table}` MODIFY COLUMN `{name}` "
                "DATETIME NULL DEFAULT CURRENT_TIMESTAMP"
            )

    def add_index(
        self, table: str, name: str, columns: list[str], unique: bool = False
    ) -> None:
        if _index_exists(self.conn, table, name):
            return
        kind = "UNIQUE INDEX" if unique else "INDEX"
        cols = ", ".join(f"`{c}`" for c in columns)
        self._exec(f"ALTER TABLE `{table}` ADD {kind} `{name}` ({cols})")

    def rename_index(self, table: str, old: str, new: str) -> None:
        if _index_exists(self.conn, table, old) and not _index_exists(
            self.conn, table, new
        ):
            self._exec(f"ALTER TABLE `{table}` RENAME INDEX `{old}` TO `{new}`")

    def add_check(self, table: str, name: str, expression: str) -> None:
        if _check_exists(self.conn, table, name):
            return
        self._exec(
            f"ALTER TABLE `{table}` ADD CONSTRAINT `{name}` CHECK ({expression})"
        )

    def sql(self, statement: str) -> None:
        self._exec(statement)


PREFLIGHT = [
    ("cards.balance NULL", "SELECT COUNT(*) FROM cards WHERE balance IS NULL"),
    ("cards.balance negativo", "SELECT COUNT(*) FROM cards WHERE balance < 0"),
    (
        "cards.daily_limit negativo",
        "SELECT COUNT(*) FROM cards WHERE daily_limit < 0",
    ),
    ("cards.status NULL", "SELECT COUNT(*) FROM cards WHERE status IS NULL"),
    (
        "products.stock NULL",
        "SELECT COUNT(*) FROM products WHERE stock IS NULL",
    ),
    ("products.stock negativo", "SELECT COUNT(*) FROM products WHERE stock < 0"),
    ("products.price negativo", "SELECT COUNT(*) FROM products WHERE price < 0"),
    ("products.cost negativo", "SELECT COUNT(*) FROM products WHERE cost < 0"),
    (
        "users.pending_balance NULL",
        "SELECT COUNT(*) FROM users WHERE pending_balance IS NULL",
    ),
    (
        "users.pending_balance negativo",
        "SELECT COUNT(*) FROM users WHERE pending_balance < 0",
    ),
    (
        "students.pending_balance NULL",
        "SELECT COUNT(*) FROM students WHERE pending_balance IS NULL",
    ),
    (
        "students.pending_balance negativo",
        "SELECT COUNT(*) FROM students WHERE pending_balance < 0",
    ),
    (
        "transactions.card_id NULL",
        "SELECT COUNT(*) FROM transactions WHERE card_id IS NULL",
    ),
    (
        "transactions.amount NULL/0",
        "SELECT COUNT(*) FROM transactions WHERE amount IS NULL OR amount = 0",
    ),
    (
        "transactions.status NULL",
        "SELECT COUNT(*) FROM transactions WHERE status IS NULL",
    ),
    (
        "transactions.reference_code duplicado",
        "SELECT COUNT(*) FROM ("
        "SELECT reference_code FROM transactions "
        "WHERE reference_code IS NOT NULL AND reference_code <> '' "
        "GROUP BY reference_code HAVING COUNT(*) > 1"
        ") dup",
    ),
    (
        "transactions.reference_code > 64",
        "SELECT COUNT(*) FROM transactions "
        "WHERE CHAR_LENGTH(reference_code) > 64",
    ),
    (
        "transactions.payment_method > 30",
        "SELECT COUNT(*) FROM transactions "
        "WHERE CHAR_LENGTH(payment_method) > 30",
    ),
    (
        "transaction_details.transaction_id NULL",
        "SELECT COUNT(*) FROM transaction_details WHERE transaction_id IS NULL",
    ),
    (
        "transaction_details.quantity NULL/<=0",
        "SELECT COUNT(*) FROM transaction_details "
        "WHERE quantity IS NULL OR quantity <= 0",
    ),
    (
        "transaction_details dinero NULL/negativo",
        "SELECT COUNT(*) FROM transaction_details "
        "WHERE unit_price IS NULL OR subtotal IS NULL "
        "OR unit_price < 0 OR subtotal < 0",
    ),
    (
        "purchase_orders.total_cost NULL",
        "SELECT COUNT(*) FROM purchase_orders WHERE total_cost IS NULL",
    ),
    (
        "purchase_order_details inválido",
        "SELECT COUNT(*) FROM purchase_order_details "
        "WHERE quantity IS NULL OR quantity <= 0 OR unit_cost IS NULL OR unit_cost < 0",
    ),
    (
        "audit_logs.action NULL",
        "SELECT COUNT(*) FROM audit_logs WHERE action IS NULL OR action = ''",
    ),
    (
        "payment_gateway_settings duplicado",
        "SELECT COUNT(*) FROM (SELECT gateway FROM payment_gateway_settings "
        "GROUP BY gateway HAVING COUNT(*) > 1) dup",
    ),
]

FINANCIAL_INVARIANT = (
    "SELECT "
    "(SELECT COALESCE(SUM(balance), 0) FROM cards), "
    "(SELECT COALESCE(SUM(amount), 0) FROM transactions WHERE "
    "(type = 'RECHARGE' AND status = 'approved') OR "
    "(type = 'PURCHASE' AND status = 'completed'))"
)


def preflight(conn) -> list[str]:
    errors = []
    for description, sql in PREFLIGHT:
        try:
            count = _scalar(conn, sql) or 0
        except Exception as exc:  # columna/tabla ausente en una base ya migrada
            errors.append(f"[PRE] No se pudo evaluar '{description}': {exc}")
            continue
        if count:
            errors.append(f"[PRE] {description}: {count} fila(s)")
    try:
        balance, net = conn.execute(text(FINANCIAL_INVARIANT)).one()
        balance = Decimal(str(balance or 0)).quantize(Decimal("0.01"))
        net = Decimal(str(net or 0)).quantize(Decimal("0.01"))
        if balance != net:
            errors.append(
                f"[PRE] Saldo de tarjetas ({balance}) != neto de movimientos ({net})"
            )
    except Exception as exc:
        errors.append(f"[PRE] No se pudo evaluar el invariante financiero: {exc}")
    return errors


def pending_warnings(conn) -> list[str]:
    pending = _scalar(
        conn,
        "SELECT COUNT(*) FROM transactions WHERE "
        "type = 'RECHARGE' AND status = 'pending'",
    )
    if pending:
        return [
            f"[WARN] {pending} recarga(s) pendientes de antes de la migración; "
            "quedan visibles para conciliación"
        ]
    return []


def migrate(m: Migrator) -> None:
    # --- users -------------------------------------------------------------
    m.add_column("users", "must_change_password", "TINYINT(1) NOT NULL DEFAULT 0")
    m.drop_default("users", "must_change_password")
    m.add_column("users", "token_version", "INT NOT NULL DEFAULT 0")
    m.drop_default("users", "token_version")
    m.add_column("users", "failed_login_attempts", "INT NOT NULL DEFAULT 0")
    m.add_column("users", "locked_until", "DATETIME NULL")
    m.modify_column("users", "pending_balance", MONEY, nullable=False)
    m.add_index("users", "ix_users_id", ["id"])
    m.normalize_now_default("users", "created_at")

    # --- password_reset_tokens --------------------------------------------
    if not _table_exists(m.conn, "password_reset_tokens"):
        m.sql(
            "CREATE TABLE `password_reset_tokens` ("
            "`id` INT NOT NULL AUTO_INCREMENT, "
            "`user_id` INT NOT NULL, "
            "`token_hash` VARCHAR(64) NOT NULL, "
            "`purpose` VARCHAR(32) NOT NULL, "
            "`expires_at` DATETIME NOT NULL, "
            "`used_at` DATETIME NULL, "
            "`created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP, "
            "PRIMARY KEY (`id`), "
            "CONSTRAINT `password_reset_tokens_ibfk_1` FOREIGN KEY (`user_id`) "
            "REFERENCES `users` (`id`) ON DELETE CASCADE"
            ") ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci"
        )
    m.add_index("password_reset_tokens", "ix_password_reset_tokens_id", ["id"])
    m.add_index(
        "password_reset_tokens", "ix_password_reset_tokens_user_id", ["user_id"]
    )
    m.add_index(
        "password_reset_tokens",
        "ix_password_reset_tokens_token_hash",
        ["token_hash"],
        unique=True,
    )
    m.add_index(
        "password_reset_tokens",
        "ix_password_reset_user_created",
        ["user_id", "created_at"],
    )

    # --- students ----------------------------------------------------------
    m.modify_column("students", "pending_balance", MONEY, nullable=False)
    m.add_index("students", "ix_students_id", ["id"])

    # --- cards -------------------------------------------------------------
    m.modify_column("cards", "balance", MONEY, nullable=False)
    m.modify_column("cards", "daily_limit", MONEY, nullable=True)
    m.modify_column("cards", "status", "ENUM('ACTIVE','BLOCKED')", nullable=False)
    m.rename_index("cards", "student_id", "uq_cards_student_id")
    m.rename_index("cards", "user_id", "uq_cards_user_id")

    # --- products ----------------------------------------------------------
    m.modify_column("products", "price", MONEY, nullable=False)
    m.modify_column("products", "cost", MONEY, nullable=False)
    m.modify_column("products", "stock", "INT", nullable=False)

    # --- transactions ------------------------------------------------------
    m.add_column("transactions", "credited_at", "DATETIME NULL")
    m.add_column("transactions", "reversed_at", "DATETIME NULL")
    m.add_column("transactions", "reversed_by_id", "INT NULL")
    m.add_column("transactions", "updated_at", "DATETIME NULL")

    m.sql(
        "UPDATE `transactions` SET `credited_at` = `timestamp` "
        "WHERE `type` = 'RECHARGE' AND `status` = 'approved' "
        "AND `credited_at` IS NULL"
    )
    m.sql(
        "UPDATE `transactions` SET `updated_at` = `timestamp` "
        "WHERE `updated_at` IS NULL"
    )
    m.sql(
        "ALTER TABLE `transactions` MODIFY COLUMN `updated_at` "
        "DATETIME NULL DEFAULT CURRENT_TIMESTAMP"
    )

    m.modify_column("transactions", "amount", MONEY, nullable=False)
    m.modify_column("transactions", "card_id", "INT", nullable=False)
    m.modify_column("transactions", "status", "VARCHAR(20)", nullable=False)
    m.modify_column("transactions", "reference_code", "VARCHAR(64)", nullable=True)
    m.modify_column("transactions", "payment_method", "VARCHAR(30)", nullable=True)
    m.drop_default("transactions", "gateway")
    m.drop_default("transactions", "currency")
    m.normalize_now_default("transactions", "timestamp")

    if not _fk_on_column_exists(m.conn, "transactions", "reversed_by_id"):
        m.sql(
            "ALTER TABLE `transactions` ADD FOREIGN KEY (`reversed_by_id`) "
            "REFERENCES `users` (`id`)"
        )

    if _column(m.conn, "transactions", "external_id") is not None:
        remaining = _scalar(
            m.conn,
            "SELECT COUNT(*) FROM transactions "
            "WHERE external_id IS NOT NULL AND external_id <> ''",
        )
        if remaining:
            raise RuntimeError(
                f"transactions.external_id tiene {remaining} valor(es); "
                "revise el backup antes de eliminar la columna"
            )
        m.sql("ALTER TABLE `transactions` DROP COLUMN `external_id`")

    m.rename_index("transactions", "card_id", "ix_transactions_card_id")
    m.rename_index("transactions", "idx_transactions_cus", "ix_transactions_cus")
    m.add_index("transactions", "ix_transactions_timestamp", ["timestamp"])
    m.add_index(
        "transactions",
        "ix_transactions_reference_code",
        ["reference_code"],
        unique=True,
    )
    m.add_index("transactions", "ix_transactions_gateway", ["gateway"])
    m.add_index(
        "transactions", "ix_transactions_card_timestamp", ["card_id", "timestamp"]
    )
    m.add_index(
        "transactions", "ix_transactions_status_type", ["status", "type"]
    )
    m.add_index(
        "transactions",
        "ix_transactions_gateway_reference",
        ["gateway", "reference_code"],
    )

    # --- transaction_details ----------------------------------------------
    m.modify_column("transaction_details", "quantity", "INT", nullable=False)
    m.modify_column("transaction_details", "transaction_id", "INT", nullable=False)
    m.modify_column("transaction_details", "unit_price", MONEY, nullable=False)
    m.modify_column("transaction_details", "subtotal", MONEY, nullable=False)
    m.rename_index(
        "transaction_details",
        "transaction_id",
        "ix_transaction_details_transaction_id",
    )

    # --- audit_logs --------------------------------------------------------
    m.modify_column("audit_logs", "action", "VARCHAR(50)", nullable=False)
    m.add_column("audit_logs", "entity", "VARCHAR(30) NULL")
    m.add_column("audit_logs", "entity_id", "INT NULL")
    m.add_column("audit_logs", "ip", "VARCHAR(45) NULL")
    m.rename_index("audit_logs", "user_id", "ix_audit_logs_user_id")
    m.add_index("audit_logs", "ix_audit_logs_action", ["action"])
    m.add_index("audit_logs", "ix_audit_logs_timestamp", ["timestamp"])
    m.normalize_now_default("audit_logs", "timestamp")

    # --- purchase_orders ---------------------------------------------------
    m.modify_column("purchase_orders", "total_cost", MONEY, nullable=False)
    m.modify_column("purchase_order_details", "unit_cost", MONEY, nullable=False)
    m.normalize_now_default("purchase_orders", "timestamp")
    m.normalize_now_default("stock_adjustments", "timestamp")

    # --- payment_notifications --------------------------------------------
    if not _table_exists(m.conn, "payment_notifications"):
        m.sql(
            "CREATE TABLE `payment_notifications` ("
            "`id` INT NOT NULL AUTO_INCREMENT, "
            "`reference_code` VARCHAR(64) NULL, "
            "`gateway` VARCHAR(30) NOT NULL, "
            "`raw` TEXT NULL, "
            "`remote_ip` VARCHAR(45) NULL, "
            "`signature_valid` TINYINT(1) NOT NULL, "
            "`reason` VARCHAR(255) NULL, "
            "`created_at` DATETIME NULL DEFAULT CURRENT_TIMESTAMP, "
            "PRIMARY KEY (`id`)"
            ") ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci"
        )
    m.add_index("payment_notifications", "ix_payment_notifications_id", ["id"])
    m.add_index(
        "payment_notifications",
        "ix_payment_notifications_reference_code",
        ["reference_code"],
    )
    m.add_index(
        "payment_notifications",
        "ix_payment_notifications_created_at",
        ["created_at"],
    )

    # --- payment_gateway_settings -----------------------------------------
    m.sql(
        "DELETE FROM `payment_gateway_settings` "
        "WHERE `gateway` NOT IN ('payu')"
    )
    m.add_index("payment_gateway_settings", "ix_payment_gateway_settings_id", ["id"])
    m.add_index(
        "payment_gateway_settings",
        "ix_payment_gateway_settings_gateway",
        ["gateway"],
        unique=True,
    )

    # --- CHECK constraints -------------------------------------------------
    if _check_constraints_supported(m.conn):
        checks = [
            ("users", "ck_users_pending_balance_non_negative", "pending_balance >= 0"),
            ("users", "ck_users_token_version_non_negative", "token_version >= 0"),
            (
                "users",
                "ck_users_failed_login_attempts_non_negative",
                "failed_login_attempts >= 0",
            ),
            (
                "students",
                "ck_students_pending_balance_non_negative",
                "pending_balance >= 0",
            ),
            ("products", "ck_products_price_non_negative", "price >= 0"),
            ("products", "ck_products_cost_non_negative", "cost >= 0"),
            ("products", "ck_products_stock_non_negative", "stock >= 0"),
            (
                "products",
                "ck_products_low_stock_threshold_non_negative",
                "low_stock_threshold >= 0",
            ),
            ("cards", "ck_cards_balance_non_negative", "balance >= 0"),
            (
                "cards",
                "ck_cards_daily_limit_non_negative",
                "daily_limit IS NULL OR daily_limit >= 0",
            ),
            (
                "transactions",
                "ck_transactions_amount_non_zero",
                "amount <> 0",
            ),
            (
                "transaction_details",
                "ck_transaction_details_quantity_positive",
                "quantity > 0",
            ),
            (
                "transaction_details",
                "ck_transaction_details_price_non_negative",
                "unit_price >= 0",
            ),
            (
                "transaction_details",
                "ck_transaction_details_subtotal_non_negative",
                "subtotal >= 0",
            ),
            (
                "purchase_order_details",
                "ck_purchase_details_quantity_positive",
                "quantity > 0",
            ),
            (
                "purchase_order_details",
                "ck_purchase_details_unit_cost_non_negative",
                "unit_cost >= 0",
            ),
        ]
        for table, name, expression in checks:
            m.add_check(table, name, expression)


SCHEMA_EXPECTATIONS = {
    "users": {
        "columns": {
            "must_change_password": ("tinyint(1)", False),
            "token_version": ("int", False),
            "failed_login_attempts": ("int", False),
            "locked_until": ("datetime", True),
            "pending_balance": ("decimal(12,2)", False),
        },
        "indexes": ["ix_users_id"],
    },
    "students": {
        "columns": {"pending_balance": ("decimal(12,2)", False)},
        "indexes": ["ix_students_id"],
    },
    "cards": {
        "columns": {
            "balance": ("decimal(12,2)", False),
            "daily_limit": ("decimal(12,2)", True),
            "status": ("enum('ACTIVE','BLOCKED')", False),
        },
        "indexes": ["uq_cards_student_id", "uq_cards_user_id"],
    },
    "products": {
        "columns": {
            "price": ("decimal(12,2)", False),
            "cost": ("decimal(12,2)", False),
            "stock": ("int", False),
        },
        "indexes": [],
    },
    "transactions": {
        "columns": {
            "amount": ("decimal(12,2)", False),
            "card_id": ("int", False),
            "status": ("varchar(20)", False),
            "reference_code": ("varchar(64)", True),
            "payment_method": ("varchar(30)", True),
            "credited_at": ("datetime", True),
            "reversed_at": ("datetime", True),
            "reversed_by_id": ("int", True),
            "updated_at": ("datetime", True),
        },
        "indexes": [
            "ix_transactions_card_id",
            "ix_transactions_cus",
            "ix_transactions_timestamp",
            "ix_transactions_reference_code",
            "ix_transactions_gateway",
            "ix_transactions_card_timestamp",
            "ix_transactions_status_type",
            "ix_transactions_gateway_reference",
        ],
    },
    "transaction_details": {
        "columns": {
            "transaction_id": ("int", False),
            "quantity": ("int", False),
            "unit_price": ("decimal(12,2)", False),
            "subtotal": ("decimal(12,2)", False),
        },
        "indexes": ["ix_transaction_details_transaction_id"],
    },
    "audit_logs": {
        "columns": {
            "action": ("varchar(50)", False),
            "entity": ("varchar(30)", True),
            "entity_id": ("int", True),
            "ip": ("varchar(45)", True),
        },
        "indexes": [
            "ix_audit_logs_user_id",
            "ix_audit_logs_action",
            "ix_audit_logs_timestamp",
        ],
    },
    "purchase_orders": {
        "columns": {"total_cost": ("decimal(12,2)", False)},
        "indexes": [],
    },
    "purchase_order_details": {
        "columns": {"unit_cost": ("decimal(12,2)", False)},
        "indexes": [],
    },
    "payment_notifications": {
        "columns": {
            "reference_code": ("varchar(64)", True),
            "gateway": ("varchar(30)", False),
            "signature_valid": ("tinyint(1)", False),
        },
        "indexes": [
            "ix_payment_notifications_reference_code",
            "ix_payment_notifications_created_at",
        ],
    },
    "password_reset_tokens": {
        "columns": {
            "token_hash": ("varchar(64)", False),
            "purpose": ("varchar(32)", False),
            "expires_at": ("datetime", False),
        },
        "indexes": ["ix_password_reset_tokens_token_hash"],
    },
}


def verify_schema(conn) -> list[str]:
    errors = []
    for table, spec in SCHEMA_EXPECTATIONS.items():
        if not _table_exists(conn, table):
            errors.append(f"[VER] Falta la tabla {table}")
            continue
        for column, (expected_type, nullable) in spec["columns"].items():
            info = _column(conn, table, column)
            if info is None:
                errors.append(f"[VER] Falta {table}.{column}")
                continue
            actual_type = (info[0] or "").lower().replace(" ", "")
            normalized_expected = expected_type.lower().replace(" ", "")
            if actual_type != normalized_expected or (info[1] == "YES") != nullable:
                errors.append(
                    f"[VER] {table}.{column}: {info[0]} nullable={info[1]} "
                    f"(esperado {expected_type} nullable={nullable})"
                )
        for index in spec["indexes"]:
            if not _index_exists(conn, table, index):
                errors.append(f"[VER] Falta el índice {table}.{index}")
    if _column(conn, "transactions", "external_id") is not None:
        errors.append("[VER] transactions.external_id sigue existiendo")
    return errors


def check_revision(conn) -> list[str]:
    if not _table_exists(conn, "alembic_version"):
        return []
    version = _scalar(conn, "SELECT version_num FROM alembic_version")
    if version not in (None, HEAD_REVISION):
        return [
            f"[PRE] alembic_version={version}; se esperaba {HEAD_REVISION} o sin tabla"
        ]
    return []


def print_snapshot(label: str, data: dict) -> None:
    print(f"[SNAP] {label}")
    for table, info in data.items():
        print(f"       {table:<28} filas={info['rows']:<5} sha256={info['sha256'][:16]}")


def compare_snapshots(before: dict, after: dict) -> list[str]:
    errors = []
    for table, info in before.items():
        current = after.get(table)
        if not current:
            errors.append(f"[SNAP] {table} desapareció")
            continue
        if info["rows"] != current["rows"]:
            errors.append(
                f"[SNAP] {table}: filas {info['rows']} -> {current['rows']}"
            )
        if info["sha256"] != current["sha256"]:
            errors.append(f"[SNAP] {table}: contenido cambiado")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Adopción de esquema legacy")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--check", action="store_true", help="Solo valida")
    group.add_argument("--apply", action="store_true", help="Aplica los cambios")
    parser.add_argument(
        "--report", default="migration_report.json", help="Ruta del reporte JSON"
    )
    args = parser.parse_args()

    if args.apply and os.getenv("ALLOW_LEGACY_MIGRATION") != "true":
        print(
            "[ABORT] Define ALLOW_LEGACY_MIGRATION=true para aplicar cambios",
            file=sys.stderr,
        )
        return 1

    with engine.connect() as conn:
        if conn.dialect.name != "mysql":
            print("[ABORT] Solo se soporta MySQL", file=sys.stderr)
            return 1

        errors = check_revision(conn) + preflight(conn)
        warnings = pending_warnings(conn)
        before = snapshot(conn)
        if args.check:
            print_snapshot("antes", before)
            for warning in warnings:
                print(warning)
            if errors:
                for error in errors:
                    print(error, file=sys.stderr)
                return 1
            print("[CHECK] Datos compatibles con el esquema nuevo")
            return 0

        if errors:
            for error in errors:
                print(error, file=sys.stderr)
            print("[ABORT] Corrige los datos antes de migrar", file=sys.stderr)
            return 1

        print_snapshot("antes", before)
        for warning in warnings:
            print(warning)
        migrator = Migrator(conn)
        try:
            migrate(migrator)
        except Exception as exc:
            print(f"[FAIL] Migración interrumpida: {exc}", file=sys.stderr)
            print(
                "[FAIL] Restaura el backup antes de reintentar", file=sys.stderr
            )
            return 1

        after = snapshot(conn)
        print_snapshot("después", after)
        post_errors = verify_schema(conn) + preflight(conn)
        post_errors += compare_snapshots(before, after)

        gateway_rows = _scalar(
            conn, "SELECT COUNT(*) FROM payment_gateway_settings"
        )
        report = {
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "database": engine.url.database,
            "statements": migrator.applied,
            "before": before,
            "after": after,
            "gateway_rows": gateway_rows,
            "errors": post_errors,
        }
        Path(args.report).write_text(
            json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8"
        )

        if post_errors:
            for error in post_errors:
                print(error, file=sys.stderr)
            print(f"[FAIL] Revisa {args.report}", file=sys.stderr)
            return 1

        print(
            f"[OK] Esquema adoptado. Pasarelas restantes: {gateway_rows}. "
            f"Reporte: {args.report}"
        )
        print("[OK] Siguiente: alembic stamp 0002_auth_hardening && alembic upgrade head")
        return 0


if __name__ == "__main__":
    sys.exit(main())
