import hmac
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text

from app.api.api_v1.api import api_router
from app.core.config import settings
from app.core.logging import RequestContextMiddleware, configure_logging
from app.db.session import engine

BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

configure_logging()

IS_PRODUCTION = settings.ENVIRONMENT.lower() == "production"

app = FastAPI(
    title=settings.PROJECT_NAME,
    version="1.0.0",
    docs_url=None if IS_PRODUCTION else "/docs",
    redoc_url=None if IS_PRODUCTION else "/redoc",
    openapi_url=None if IS_PRODUCTION else f"{settings.API_V1_STR}/openapi.json",
)

CSRF_UNSAFE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}
CSRF_EXEMPT_PATHS = {
    f"{settings.API_V1_STR}/auth/login/access-token",
    f"{settings.API_V1_STR}/auth/logout",
    f"{settings.API_V1_STR}/auth/password-recovery",
    f"{settings.API_V1_STR}/auth/reset-password",
}


@app.middleware("http")
async def csrf_protection(request: Request, call_next):
    """Double-submit CSRF solo cuando la sesión viaja en cookie."""
    uses_cookie_session = settings.AUTH_COOKIE_NAME in request.cookies
    if (
        uses_cookie_session
        and request.method in CSRF_UNSAFE_METHODS
        and request.url.path not in CSRF_EXEMPT_PATHS
    ):
        cookie_token = request.cookies.get(settings.CSRF_COOKIE_NAME, "")
        header_token = request.headers.get(settings.CSRF_HEADER_NAME, "")
        if (
            not cookie_token
            or not header_token
            or not hmac.compare_digest(cookie_token, header_token)
        ):
            return JSONResponse(
                status_code=403,
                content={"detail": "Token CSRF inválido o ausente"},
            )
    return await call_next(request)


raw_origins = [origin.strip() for origin in settings.ALLOWED_ORIGINS.split(",") if origin.strip()]
# Con cookies el wildcard es inválido: si hay orígenes explícitos se descarta "*"; si solo hay "*", sin credenciales.
origins = [origin for origin in raw_origins if origin != "*"]
allow_credentials = bool(origins)
if not origins and "*" in raw_origins:
    origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(RequestContextMiddleware)

app.include_router(api_router, prefix=settings.API_V1_STR)

app.mount("/uploads", StaticFiles(directory=str(UPLOAD_DIR)), name="uploads")


@app.get("/")
def read_root():
    return {"message": "School POS System API is running"}


@app.get("/health")
def health():
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception:
        raise HTTPException(status_code=503, detail="Base de datos no disponible")
    return {"status": "ok"}
