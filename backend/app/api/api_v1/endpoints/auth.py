from datetime import timedelta
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.crud import crud_user
from app.core import security
from app.core.config import settings
from app.schemas.token import Token
from app.utils.email_sender import send_recovery_email
from app.schemas.user import UserUpdate
from app.api import deps
from app.models.user import User

router = APIRouter()

@router.post("/login/access-token", response_model=Token)
def login_access_token(
    db: Session = Depends(get_db), 
    form_data: OAuth2PasswordRequestForm = Depends()
) -> Any:
    """
    OAuth2 compatible token login, get an access token for future requests
    """
    # Buscamos el usuario
    user = crud_user.get_user_by_email(db, email=form_data.username) # OAuth2 usa 'username' aunque sea email
    
    # Validamos password
    if not user or not security.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email o contraseña incorrectos",
        )
    
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Usuario inactivo")
        
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    return {
        "access_token": security.create_access_token(
            subject=user.email, expires_delta=access_token_expires
        ),
        "token_type": "bearer",
    }

@router.post("/password-recovery/{email}")
def recover_password(email: str, db: Session = Depends(get_db)):
    """
    Paso 1: Generar token y enviar email
    """
    
    user = crud_user.get_user_by_email(db, email=email)
    if not user:
        # Por seguridad, no decimos si el email existe o no
        return {"message": "Si el correo está registrado, recibirá un enlace pronto."}

    # Generamos un token JWT corto (15 min) específico para password
    password_token = security.create_access_token(
        subject=user.email, expires_delta=timedelta(minutes=15)
    )
    
    # Enviar correo
    sent = send_recovery_email(db, user.email, password_token)
    if not sent:
        raise HTTPException(status_code=500, detail="Error al enviar el correo")

    return {"message": "Correo de recuperación enviado"}

@router.post("/reset-password")
def reset_password(token: str, new_password: str, db: Session = Depends(get_db)):
    """
    Paso 2: Validar token y cambiar contraseña
    """
    # Validar token (reutilizamos lógica de deps.py pero manual)
    email = security.verify_token(token) # Necesitarás crear esta función simple en security.py
    if not email:
        raise HTTPException(status_code=400, detail="Token inválido o expirado")
    
    user = crud_user.get_user_by_email(db, email=email)
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    
    # Actualizar password
    crud_user.update_user(db, db_user=user, user_in={"password": new_password})
    return {"message": "Contraseña actualizada con éxito"}
