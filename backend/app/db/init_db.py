"""Seed idempotente de la base de datos.

Uso:
    python -m app.db.init_db
    python -m app.db.init_db --check

No ejecuta DDL: el esquema se crea con `alembic upgrade head`.
"""

import argparse
import sys
from decimal import Decimal

from sqlalchemy import inspect

from app.core.config import settings
from app.core.secret_store import encrypt_secret, is_encrypted
from app.core.security import get_password_hash, validate_password
from app.crud import crud_payment_gateway
from app.db.base import Base
from app.db.session import SessionLocal
from app.models.payment_gateway_settings import PaymentGatewaySetting
from app.models.setting import SystemSetting
from app.models.user import User, UserRole


def seed_gateways(db) -> None:
    crud_payment_gateway.seed_gateway_settings(db)


def encrypt_existing_secrets(db) -> bool:
    """Cifra secretos que hayan quedado en texto plano de instalaciones previas."""
    changed = False
    row = (
        db.query(SystemSetting)
        .filter(SystemSetting.key == "smtp_pass")
        .first()
    )
    if row and row.value and not is_encrypted(row.value):
        row.value = encrypt_secret(row.value)
        db.commit()
        changed = True
    return changed


def seed_admin(db) -> bool:
    """Crea el admin inicial solo si no existe. Nunca cambia una clave existente."""
    if not settings.ADMIN_EMAIL or not settings.ADMIN_INITIAL_PASSWORD:
        return False

    validate_password(settings.ADMIN_INITIAL_PASSWORD)

    email = settings.ADMIN_EMAIL.strip().lower()
    existing = db.query(User).filter(User.email == email).first()
    if existing:
        return False

    admin = User(
        full_name="Administrador del Sistema",
        email=email,
        hashed_password=get_password_hash(settings.ADMIN_INITIAL_PASSWORD),
        role=UserRole.ADMIN,
        is_active=True,
        must_change_password=settings.ADMIN_FORCE_CHANGE,
        token_version=0,
        pending_balance=Decimal("0.00"),
    )
    db.add(admin)
    db.commit()
    return True


def check_database(db) -> list[str]:
    errors: list[str] = []
    inspector = inspect(db.bind)

    existing_tables = set(inspector.get_table_names())
    missing = sorted(set(Base.metadata.tables) - existing_tables)
    if missing:
        errors.append(f"Faltan tablas: {', '.join(missing)}")

    if "payment_gateway_settings" in existing_tables:
        payu = (
            db.query(PaymentGatewaySetting)
            .filter(
                PaymentGatewaySetting.gateway == "payu",
                PaymentGatewaySetting.is_active.is_(True),
            )
            .first()
        )
        if not payu:
            errors.append("PayU no está sembrado como pasarela activa")

    if "users" in existing_tables:
        active_admins = (
            db.query(User)
            .filter(User.role == UserRole.ADMIN, User.is_active.is_(True))
            .count()
        )
        if active_admins == 0:
            errors.append("No hay ningún administrador activo")

    if "system_settings" in existing_tables:
        smtp = (
            db.query(SystemSetting)
            .filter(SystemSetting.key == "smtp_pass")
            .first()
        )
        if smtp and smtp.value and not is_encrypted(smtp.value):
            errors.append(
                "smtp_pass está en texto plano; ejecute el seed para cifrarlo"
            )

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Seed/verificación de School POS")
    parser.add_argument(
        "--check",
        action="store_true",
        help="Solo verifica esquema y datos mínimos, sin escribir.",
    )
    args = parser.parse_args()

    with SessionLocal() as db:
        if args.check:
            errors = check_database(db)
            if errors:
                for error in errors:
                    print(f"[CHECK][ERROR] {error}", file=sys.stderr)
                return 1
            print("[CHECK] Esquema y datos mínimos OK")
            return 0

        try:
            seed_gateways(db)
            encrypt_existing_secrets(db)
            created = seed_admin(db)
        except ValueError as exc:
            print(f"[SEED][ERROR] {exc}", file=sys.stderr)
            return 1

        if created:
            print("[SEED] Administrador inicial creado")
        else:
            print("[SEED] Administrador inicial sin cambios")
        print("[SEED] Pasarelas de pago listas (solo PayU)")
        return 0


if __name__ == "__main__":
    sys.exit(main())
