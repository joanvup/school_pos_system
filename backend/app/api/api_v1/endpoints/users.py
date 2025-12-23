from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional

from app.db.session import get_db
from app.schemas.user import UserCreate, UserResponse, UserUpdate
from app.crud import crud_user
from app.api import deps
from app.models.user import User

router = APIRouter()

@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(user: UserCreate, db: Session = Depends(get_db)):
    """
    Crear un nuevo usuario (Admin, Padre, Empleado, etc).
    """
    # 1. Validar si existe
    db_user = crud_user.get_user_by_email(db, email=user.email)
    if db_user:
        raise HTTPException(
            status_code=400, 
            detail="El email ya está registrado en el sistema."
        )
    
    # 2. Crear
    return crud_user.create_user(db=db, user=user)

@router.get("/", response_model=List[UserResponse])
def read_users(
    skip: int = 0, 
    limit: int = 20, # Default bajado a 20 para probar paginación
    search: Optional[str] = None, # Nuevo parámetro
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.get_current_active_admin) # Solo admin puede ver/buscar
):
    """
    Obtener lista de usuarios con paginación y búsqueda.
    """
    users = crud_user.get_users(db, skip=skip, limit=limit, search=search)
    return users

@router.put("/{user_id}", response_model=UserResponse)
def update_user_admin(
    user_id: int,
    user_in: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.get_current_active_admin)
):
    """
    ADMIN: Actualizar datos de un usuario (incluyendo password).
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    
    user = crud_user.update_user(db, db_user=user, user_in=user_in)
    return user

@router.get("/me", response_model=UserResponse)
def read_user_me(
    current_user: User = Depends(deps.get_current_active_user),
):
    """
    Obtener datos del usuario logueado actualmente.
    """
    return current_user