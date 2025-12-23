from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.core.config import settings

# Crear motor de base de datos
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True, # Verifica conexión antes de usarla
    echo=False # Cambiar a True para ver SQL en consola (debug)
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# Dependencia para inyectar sesión en endpoints
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()