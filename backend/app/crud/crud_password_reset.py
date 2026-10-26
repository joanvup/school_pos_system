from datetime import datetime, timezone
from hashlib import sha256
from typing import Optional

from sqlalchemy.orm import Session

from app.models.password_reset_token import PasswordResetToken


def hash_token(raw_token: str) -> str:
    return sha256(raw_token.encode("utf-8")).hexdigest()


def invalidate_active(db: Session, user_id: int, now: Optional[datetime] = None) -> None:
    db.query(PasswordResetToken).filter(
        PasswordResetToken.user_id == user_id,
        PasswordResetToken.used_at.is_(None),
    ).update(
        {
            PasswordResetToken.used_at: now
            or datetime.now(timezone.utc).replace(tzinfo=None)
        },
        synchronize_session=False,
    )


def create(
    db: Session,
    user_id: int,
    token_hash: str,
    expires_at: datetime,
    purpose: str = "password_reset",
) -> PasswordResetToken:
    row = PasswordResetToken(
        user_id=user_id,
        token_hash=token_hash,
        purpose=purpose,
        expires_at=expires_at,
    )
    db.add(row)
    return row


def get_valid_for_update(
    db: Session,
    token_hash: str,
    now: datetime,
    purpose: str = "password_reset",
) -> Optional[PasswordResetToken]:
    return (
        db.query(PasswordResetToken)
        .filter(
            PasswordResetToken.token_hash == token_hash,
            PasswordResetToken.purpose == purpose,
            PasswordResetToken.used_at.is_(None),
            PasswordResetToken.expires_at > now,
        )
        .with_for_update()
        .first()
    )
