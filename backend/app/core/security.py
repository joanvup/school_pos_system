from datetime import datetime, timedelta, timezone
from typing import Any, Optional, Union
from uuid import uuid4

import jwt
from jwt import PyJWTError
from passlib.context import CryptContext

from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
ALGORITHM = "HS256"

COMMON_PASSWORDS = {
    "123456",
    "12345678",
    "123456789",
    "1234567890",
    "password",
    "password1",
    "admin123",
    "admin1234",
    "admin123_seguro",
    "administrador",
    "empleado123",
    "colegio123",
    "qwerty123",
    "bienvenido",
    "contraseña",
}

# Hash descartable para igualar el tiempo de respuesta cuando el email no existe.
DUMMY_PASSWORD_HASH = pwd_context.hash("school-pos-dummy-password-never-valid")


class InvalidTokenError(Exception):
    """Token ausente, mal formado, expirado o con claims inválidos."""


def utcnow() -> datetime:
    """UTC naive, que es lo que devuelve MySQL en columnas DATETIME."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def validate_password(password: str) -> str:
    """Reglas mínimas compartidas por alta, reset, cambio e importación."""
    if not isinstance(password, str) or len(password) < 10:
        raise ValueError("La contraseña debe tener al menos 10 caracteres")
    if len(password.encode("utf-8")) > 72:
        raise ValueError("La contraseña no puede superar 72 bytes")
    if password.strip().lower() in COMMON_PASSWORDS:
        raise ValueError("La contraseña es demasiado común")
    if not any(c.isalpha() for c in password) or not any(c.isdigit() for c in password):
        raise ValueError("La contraseña debe incluir letras y números")
    return password


def create_access_token(
    subject: Union[str, Any],
    token_version: int = 0,
    expires_delta: Optional[timedelta] = None,
) -> str:
    now = datetime.now(timezone.utc)
    expire = now + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    payload = {
        "sub": str(subject),
        "typ": "access",
        "iss": settings.JWT_ISSUER,
        "aud": settings.JWT_AUDIENCE,
        "iat": now,
        "nbf": now,
        "exp": expire,
        "jti": uuid4().hex,
        "ver": int(token_version or 0),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> dict:
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[ALGORITHM],
            audience=settings.JWT_AUDIENCE,
            issuer=settings.JWT_ISSUER,
            options={
                "require": ["exp", "iat", "sub"],
                "verify_aud": True,
                "verify_iss": True,
            },
        )
    except PyJWTError as exc:
        raise InvalidTokenError("Token inválido o expirado") from exc

    if payload.get("typ") != "access":
        raise InvalidTokenError("Tipo de token no permitido")

    try:
        int(payload.get("ver", 0))
    except (TypeError, ValueError) as exc:
        raise InvalidTokenError("Versión de token inválida") from exc

    return payload


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)
