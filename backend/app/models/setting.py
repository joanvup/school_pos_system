from sqlalchemy import Column, String, Text
from app.db.session import Base

class SystemSetting(Base):
    __tablename__ = "system_settings"

    key = Column(String(50), primary_key=True, index=True) # Ej: 'school_name'
    value = Column(Text, nullable=True) # Ej: 'Colegio San José'