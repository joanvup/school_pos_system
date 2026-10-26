from typing import Optional

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core import security
from app.core.config import settings
from app.crud import crud_user
from app.db.session import get_db
from app.models.user import User, UserRole

# OAuth2PasswordBearer le dice a Swagger UI dónde obtener el token.
# auto_error=False permite usar también la cookie HttpOnly del navegador.
reusable_oauth2 = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/auth/login/access-token",
    auto_error=False,
)

# Rutas que un usuario con cambio de contraseña pendiente sí puede usar.
_PASSWORD_CHANGE_ALLOWED_PATHS = {
    f"{settings.API_V1_STR}/users/me",
    f"{settings.API_V1_STR}/auth/change-password",
    f"{settings.API_V1_STR}/auth/logout",
    f"{settings.API_V1_STR}/auth/logout-all",
}


def _unauthorized(detail: str = "No se pudo validar las credenciales") -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


def get_current_user(
    request: Request,
    db: Session = Depends(get_db),
    token: Optional[str] = Depends(reusable_oauth2),
) -> User:
    raw_token = token or request.cookies.get(settings.AUTH_COOKIE_NAME)
    if not raw_token:
        raise _unauthorized()

    try:
        payload = security.decode_access_token(raw_token)
        user_id = int(payload.get("sub"))
    except (security.InvalidTokenError, TypeError, ValueError):
        raise _unauthorized("Sesión inválida o expirada")

    user = crud_user.get_user_by_id(db, user_id)
    if not user:
        raise _unauthorized("Sesión inválida o expirada")

    # Un cambio de contraseña, desactivación o "cerrar todas las sesiones"
    # incrementa token_version e invalida los tokens anteriores.
    if int(payload.get("ver", 0)) != int(user.token_version or 0):
        raise _unauthorized("Sesión expirada. Inicie sesión nuevamente.")

    return user


def get_current_active_user(
    request: Request,
    current_user: User = Depends(get_current_user),
) -> User:
    if not current_user.is_active:
        raise HTTPException(status_code=403, detail="Usuario inactivo")

    if (
        current_user.must_change_password
        and request.url.path not in _PASSWORD_CHANGE_ALLOWED_PATHS
    ):
        raise HTTPException(
            status_code=403,
            detail="Debe cambiar la contraseña antes de continuar",
        )

    return current_user


def get_current_active_staff(
    current_user: User = Depends(get_current_active_user),
) -> User:
    if current_user.role not in [UserRole.ADMIN, UserRole.SUPERVISOR, UserRole.VENDEDOR]:
        raise HTTPException(
            status_code=403, detail="Solo el personal autorizado puede realizar esta acción"
        )
    return current_user


def get_current_active_admin(
    current_user: User = Depends(get_current_active_user),
) -> User:
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=403, detail="El usuario no tiene suficientes permisos"
        )
    return current_user


def get_current_admin_or_supervisor(
    current_user: User = Depends(get_current_active_user),
) -> User:
    if current_user.role not in [UserRole.ADMIN, UserRole.SUPERVISOR]:
        raise HTTPException(
            status_code=403,
            detail="El usuario no tiene suficientes permisos (Se requiere Admin o Supervisor)",
        )
    return current_user
