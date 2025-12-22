from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.db.session import engine
from app.db.base import Base
from app.api.api_v1.api import api_router
from app.core.config import settings
from fastapi.staticfiles import StaticFiles # Importar
import os

# Crear tablas
Base.metadata.create_all(bind=engine)

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