from sqlalchemy import (
    JSON,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import relationship

from app.db.session import Base


class ImportJob(Base):
    """Estado de una importación de Excel, compartido entre workers."""

    __tablename__ = "import_jobs"

    id = Column(String(36), primary_key=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    kind = Column(String(20), nullable=False)
    status = Column(String(20), nullable=False, default="processing")
    progress = Column(Integer, nullable=False, default=0)
    result = Column(JSON, nullable=True)
    error = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    user = relationship("User")

    __table_args__ = (Index("ix_import_jobs_user_created", "user_id", "created_at"),)


class RequestThrottle(Base):
    """Ventana fija por clave para limitar solicitudes sensibles."""

    __tablename__ = "request_throttles"

    key = Column(String(160), primary_key=True)
    window_start = Column(DateTime, nullable=False)
    count = Column(Integer, nullable=False, default=0)

    __table_args__ = (
        Index("ix_request_throttles_window_start", "window_start"),
    )
