from typing import Generator, Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.user import User, UserRole
from app.schemas.token import TokenPayload
from app.core import security
from app.core.config import settings
from app.crud import crud_user

# OAuth2PasswordBearer le dice a Swagger UI dónde obtener el token
reusable_oauth2 = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/auth/login/access-token"
)

# 1. Obtener el usuario actual basado en el token
def get_current_user(
    db: Session = Depends(get_db),
    token: str = Depends(reusable_oauth2)
) -> User:
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[security.ALGORITHM]
        )
        token_data = TokenPayload(**payload)
    except (JWTError, KeyError):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No se pudo validar las credenciales",
        )
    
    user = crud_user.get_user_by_email(db, email=token_data.sub)
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return user

# 2. Verificar que el usuario esté activo
def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Usuario inactivo")
    return current_user

# 3. Verificar que sea ADMIN (Ejemplo de Rol)
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
            status_code=403, detail="El usuario no tiene suficientes permisos (Se requiere Admin o Supervisor)"
        )
    return current_user