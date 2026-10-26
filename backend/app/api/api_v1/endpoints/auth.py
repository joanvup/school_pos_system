import logging
import secrets
from datetime import timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr, Field, field_validator
from sqlalchemy.orm import Session

from app.api import deps
from app.core import security
from app.core.config import settings
from app.crud import crud_password_reset, crud_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.token import Token
from app.utils.email_sender import send_recovery_email

router = APIRouter()
logger = logging.getLogger(__name__)

GENERIC_LOGIN_ERROR = "Email o contraseña incorrectos"
GENERIC_RECOVERY_MESSAGE = (
    "Si el correo está registrado, recibirá un enlace para restablecer la contraseña."
)
GENERIC_RESET_ERROR = "El enlace es inválido o ha expirado"


class PasswordRecoveryRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str = Field(min_length=20, max_length=200)
    new_password: str = Field(min_length=10, max_length=72)

    @field_validator("new_password")
    @classmethod
    def _password_policy(cls, value: str) -> str:
        return security.validate_password(value)


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=10, max_length=72)

    @field_validator("new_password")
    @classmethod
    def _password_policy(cls, value: str) -> str:
        return security.validate_password(value)


def _set_auth_cookies(response: Response, token: str, max_age: int) -> None:
    secure = settings.use_secure_cookies
    response.set_cookie(
        settings.AUTH_COOKIE_NAME,
        token,
        max_age=max_age,
        httponly=True,
        secure=secure,
        samesite="lax",
        path="/",
    )
    # Double-submit CSRF: el frontend copia este valor en X-CSRF-Token.
    response.set_cookie(
        settings.CSRF_COOKIE_NAME,
        secrets.token_urlsafe(32),
        max_age=max_age,
        httponly=False,
        secure=secure,
        samesite="lax",
        path="/",
    )


def _clear_auth_cookies(response: Response) -> None:
    response.delete_cookie(settings.AUTH_COOKIE_NAME, path="/")
    response.delete_cookie(settings.CSRF_COOKIE_NAME, path="/")


@router.post("/login/access-token", response_model=Token)
def login_access_token(
    response: Response,
    db: Session = Depends(get_db),
    form_data: OAuth2PasswordRequestForm = Depends(),
) -> Any:
    """Login OAuth2. Devuelve token para clientes API y cookie HttpOnly para el navegador."""
    email = crud_user.normalize_email(form_data.username)
    user = crud_user.get_user_by_email(db, email=email)
    now = security.utcnow()

    hashed_password = user.hashed_password if user else security.DUMMY_PASSWORD_HASH
    try:
        password_ok = security.verify_password(form_data.password, hashed_password)
    except Exception:
        password_ok = False

    if user and user.locked_until and user.locked_until > now:
        if not password_ok:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=GENERIC_LOGIN_ERROR,
                headers={"WWW-Authenticate": "Bearer"},
            )
        retry_after = max(1, int((user.locked_until - now).total_seconds()))
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Demasiados intentos fallidos. Intente nuevamente más tarde.",
            headers={"Retry-After": str(retry_after)},
        )

    if user and user.locked_until:
        # Bloqueo vencido: se reinicia la ventana de intentos.
        user.locked_until = None
        user.failed_login_attempts = 0
        db.commit()

    if not user or not password_ok:
        if user:
            attempts = (user.failed_login_attempts or 0) + 1
            user.failed_login_attempts = attempts
            if attempts >= settings.MAX_FAILED_LOGIN_ATTEMPTS:
                user.locked_until = now + timedelta(
                    minutes=settings.LOGIN_LOCKOUT_MINUTES
                )
                user.failed_login_attempts = 0
            db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=GENERIC_LOGIN_ERROR,
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(status_code=403, detail="Usuario inactivo")

    if user.failed_login_attempts or user.locked_until:
        user.failed_login_attempts = 0
        user.locked_until = None
        db.commit()

    expires_seconds = settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    access_token = security.create_access_token(
        subject=user.id,
        token_version=user.token_version,
        expires_delta=timedelta(seconds=expires_seconds),
    )
    _set_auth_cookies(response, access_token, expires_seconds)

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": expires_seconds,
        "must_change_password": bool(user.must_change_password),
    }


@router.post("/logout")
def logout(response: Response):
    """Cierra la sesión del navegador. Idempotente y sin CSRF (solo borra cookies)."""
    _clear_auth_cookies(response)
    return {"message": "Sesión cerrada"}


@router.post("/logout-all")
def logout_all(
    response: Response,
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.get_current_active_user),
):
    """Revoca todos los tokens del usuario, incluidos otros dispositivos."""
    current_user.token_version = (current_user.token_version or 0) + 1
    db.commit()
    _clear_auth_cookies(response)
    return {"message": "Todas las sesiones fueron cerradas"}


@router.post("/password-recovery")
def recover_password(
    payload: PasswordRecoveryRequest,
    db: Session = Depends(get_db),
):
    """Genera un token de un solo uso y envía el enlace. Respuesta uniforme."""
    email = crud_user.normalize_email(str(payload.email))
    user = crud_user.get_user_by_email(db, email=email)

    if user and user.is_active:
        now = security.utcnow()
        raw_token = secrets.token_urlsafe(32)

        crud_password_reset.invalidate_active(db, user.id, now)
        crud_password_reset.create(
            db,
            user_id=user.id,
            token_hash=crud_password_reset.hash_token(raw_token),
            expires_at=now
            + timedelta(minutes=settings.PASSWORD_RESET_EXPIRE_MINUTES),
        )
        db.commit()

        try:
            sent = send_recovery_email(db, user.email, raw_token)
        except Exception:
            logger.exception("Error enviando el correo de recuperación")
            sent = False

        if not sent:
            # No dejamos un token válido que nunca llegó al usuario.
            crud_password_reset.invalidate_active(db, user.id, security.utcnow())
            db.commit()

    return {"message": GENERIC_RECOVERY_MESSAGE}


@router.post("/reset-password")
def reset_password(
    payload: ResetPasswordRequest,
    response: Response,
    db: Session = Depends(get_db),
):
    """Consume el token una sola vez y cambia la contraseña."""
    now = security.utcnow()
    token_row = crud_password_reset.get_valid_for_update(
        db,
        token_hash=crud_password_reset.hash_token(payload.token),
        now=now,
    )
    if not token_row:
        raise HTTPException(status_code=400, detail=GENERIC_RESET_ERROR)

    user = crud_user.get_user_by_id(db, token_row.user_id)
    if not user or not user.is_active:
        raise HTTPException(status_code=400, detail=GENERIC_RESET_ERROR)

    token_row.used_at = now
    user.hashed_password = security.get_password_hash(payload.new_password)
    user.token_version = (user.token_version or 0) + 1
    user.must_change_password = False
    user.failed_login_attempts = 0
    user.locked_until = None
    db.commit()

    _clear_auth_cookies(response)
    return {"message": "Contraseña actualizada con éxito"}


@router.post("/change-password")
def change_password(
    payload: ChangePasswordRequest,
    response: Response,
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.get_current_active_user),
):
    """Cambio de contraseña autenticado; revoca las sesiones existentes."""
    if not security.verify_password(
        payload.current_password, current_user.hashed_password
    ):
        raise HTTPException(status_code=400, detail="La contraseña actual es incorrecta")

    if payload.current_password == payload.new_password:
        raise HTTPException(
            status_code=400,
            detail="La nueva contraseña debe ser diferente a la actual",
        )

    current_user.hashed_password = security.get_password_hash(payload.new_password)
    current_user.token_version = (current_user.token_version or 0) + 1
    current_user.must_change_password = False
    current_user.failed_login_attempts = 0
    current_user.locked_until = None
    db.commit()

    _clear_auth_cookies(response)
    return {"message": "Contraseña actualizada. Inicie sesión nuevamente."}
