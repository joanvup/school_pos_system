"""Límites de solicitudes persistentes, compartidos entre workers."""

import hashlib
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.ops import RequestThrottle

STALE_AFTER = timedelta(days=7)


def fingerprint(value: str) -> str:
    """Evita guardar correos u otros identificadores en claro."""
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:32]


def enforce_rate_limit(
    db: Session,
    key: str,
    *,
    limit: int,
    window_seconds: int,
) -> None:
    """Cuenta la solicitud en una ventana fija y responde 429 al exceder."""
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    window_start = now - timedelta(seconds=window_seconds)

    row = (
        db.query(RequestThrottle)
        .filter(RequestThrottle.key == key)
        .with_for_update()
        .first()
    )
    if row is None:
        try:
            # Las claves de correos/IP son ilimitadas; purgamos las ventanas
            # viejas al crear una nueva para que la tabla no crezca sin fin.
            db.query(RequestThrottle).filter(
                RequestThrottle.window_start < now - STALE_AFTER
            ).delete(synchronize_session=False)
            db.add(RequestThrottle(key=key, window_start=now, count=1))
            db.commit()
            return
        except IntegrityError:
            # Otro worker insertó la misma clave en paralelo.
            db.rollback()
            row = (
                db.query(RequestThrottle)
                .filter(RequestThrottle.key == key)
                .with_for_update()
                .first()
            )
            if row is None:
                return

    if row.window_start < window_start:
        row.window_start = now
        row.count = 1
        db.commit()
        return

    if row.count >= limit:
        retry_after = max(
            1,
            int(
                (
                    row.window_start + timedelta(seconds=window_seconds) - now
                ).total_seconds()
            ),
        )
        db.commit()
        raise HTTPException(
            status_code=429,
            detail="Demasiadas solicitudes; intenta más tarde",
            headers={"Retry-After": str(retry_after)},
        )

    row.count += 1
    db.commit()
