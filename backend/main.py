from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from app.db.session import engine
from app.db.base import Base
from app.api.api_v1.api import api_router
from app.core.config import settings
from fastapi.staticfiles import StaticFiles # Importar
from app.db.session import SessionLocal
from app.crud import crud_payment_gateway
import os

# Migraciones de columnas idempotentes.
# create_all() NO agrega columnas a tablas existentes, por eso revisamos
# information_schema y ejecutamos el ALTER solo si la columna no existe.
MIGRATIONS = [
    ("students", "ADD COLUMN pending_balance FLOAT NOT NULL DEFAULT 0"),
    ("users", "ADD COLUMN pending_balance FLOAT NOT NULL DEFAULT 0"),
    ("transactions", "ADD COLUMN gateway VARCHAR(30) DEFAULT 'payu'"),
    ("transactions", "ADD COLUMN currency VARCHAR(10) DEFAULT 'COP'"),
    ("transactions", "ADD COLUMN raw_notification TEXT"),
    ("transactions", "ADD COLUMN response_code VARCHAR(100)"),
]

def _column_exists(table: str, column: str) -> bool:
    with engine.connect() as conn:
        result = conn.execute(
            text(
                "SELECT COUNT(*) FROM information_schema.columns "
                "WHERE table_schema = DATABASE() AND table_name = :t AND column_name = :c"
            ),
            {"t": table, "c": column},
        )
        return result.scalar() > 0

def run_safe_migrations():
    for table, column_ddl in MIGRATIONS:
        column = column_ddl.replace("ADD COLUMN ", "").split(" ")[0]
        if _column_exists(table, column):
            continue
        sql = f"ALTER TABLE {table} {column_ddl}"
        print(f"[MIGRACION] Ejecutando: {sql}")
        try:
            with engine.begin() as conn:
                conn.execute(text(sql))
        except Exception as e:
            # Si el usuario de BD no tiene permisos, avisamos claramente y dejamos
            # el SQL que debe ejecutarse manualmente para no romper el arranque.
            print(f"[MIGRACION][ERROR] No se pudo ejecutar '{sql}': {e}")
            print(f"[MIGRACION][MANUAL] Ejecuta manualmente en la BD: {sql}")

# Crear tablas
Base.metadata.create_all(bind=engine)

# Aplicar migraciones pendientes
run_safe_migrations()

# Sembrar la tabla de pasarelas de pago (PayU activa por defecto)
def seed_gateways():
    try:
        with SessionLocal() as db:
            crud_payment_gateway.seed_gateway_settings(db)
    except Exception as e:
        print(f"[SEED] No se pudo sembrar pasarelas: {e}")

seed_gateways()

app = FastAPI(
    title=settings.PROJECT_NAME,
    version="1.0.0",
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

# Procesamos la cadena del .env para convertirla en una lista de Python
if settings.ALLOWED_ORIGINS == "*":
    origins = ["*"]
else:
    # Si en el .env pusiste: https://dominio.com,http://localhost:5173
    # esto lo convertirá en ['https://dominio.com', 'http://localhost:5173']
    origins = [origin.strip() for origin in settings.ALLOWED_ORIGINS.split(",")]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.API_V1_STR)

# Crear carpeta si no existe
if not os.path.exists("uploads"):
    os.makedirs("uploads")
# Montar la carpeta para que las imágenes sean accesibles vía URL
# Ejemplo: http://localhost:8000/uploads/imagen.jpg
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

@app.get("/")
def read_root():
    return {"message": "School POS System API is secure and running"}