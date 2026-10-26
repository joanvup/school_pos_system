"""Reinicia la base de datos de School POS.

Operación destructiva. Solo se ejecuta si:
  - ALLOW_DB_RESET=true
  - se pasa --yes-i-have-a-backup
  - no existen movimientos (transactions, purchase_orders, stock_adjustments)

Después de este script hay que ejecutar `alembic upgrade head` y el seed.
"""

import argparse
import os
import re
import sys

from sqlalchemy import create_engine, inspect, text

from app.core.config import settings


def _count(engine, table: str) -> int:
    if table not in inspect(engine).get_table_names():
        return 0
    with engine.connect() as conn:
        return conn.execute(text(f"SELECT COUNT(*) FROM `{table}`")).scalar() or 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Reset destructivo de la base de datos")
    parser.add_argument("--yes-i-have-a-backup", action="store_true")
    args = parser.parse_args()

    if os.getenv("ALLOW_DB_RESET") != "true":
        print("[RESET][ABORT] Define ALLOW_DB_RESET=true", file=sys.stderr)
        return 1
    if not args.yes_i_have_a_backup:
        print("[RESET][ABORT] Falta --yes-i-have-a-backup", file=sys.stderr)
        return 1

    engine = create_engine(settings.DATABASE_URL)
    if engine.dialect.name != "mysql":
        print("[RESET][ABORT] Solo se soporta MySQL", file=sys.stderr)
        return 1

    movements = {
        "transactions": _count(engine, "transactions"),
        "purchase_orders": _count(engine, "purchase_orders"),
        "stock_adjustments": _count(engine, "stock_adjustments"),
    }
    pending = {table: count for table, count in movements.items() if count > 0}
    if pending:
        print(f"[RESET][ABORT] Hay movimientos: {pending}", file=sys.stderr)
        return 1

    database = engine.url.database or ""
    if not re.fullmatch(r"[A-Za-z0-9_]+", database):
        print("[RESET][ABORT] Nombre de base de datos inválido", file=sys.stderr)
        return 1

    with engine.connect() as conn:
        conn.execute(text(f"DROP DATABASE `{database}`"))
        conn.execute(
            text(
                f"CREATE DATABASE `{database}` "
                "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
            )
        )
        conn.commit()

    print(f"[RESET] Base {database} recreada vacía")
    print("[RESET] Siguiente: alembic upgrade head && python -m app.db.init_db")
    return 0


if __name__ == "__main__":
    sys.exit(main())
