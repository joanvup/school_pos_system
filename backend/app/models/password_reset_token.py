from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, String, func
from sqlalchemy.orm import relationship

from app.db.session import Base


class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # Solo se guarda el SHA-256; el token en claro nunca se persiste.
    token_hash = Column(String(64), unique=True, nullable=False, index=True)
    purpose = Column(String(32), nullable=False, default="password_reset")
    expires_at = Column(DateTime, nullable=False)
    used_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    user = relationship("User")

    __table_args__ = (
        Index("ix_password_reset_user_created", "user_id", "created_at"),
    )
