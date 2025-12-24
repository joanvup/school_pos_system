from sqlalchemy.orm import Session
from sqlalchemy import and_, or_ 
from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate
from app.core.security import get_password_hash
from typing import Union, Dict, Any
from fastapi import HTTPException

def get_user_by_email(db: Session, email: str):
    return db.query(User).filter(User.email == email).first()

def get_users(db: Session, skip: int = 0, limit: int = 100, search: str = None):
    query = db.query(User)
    
    if search:
        # 1. Dividimos el texto de búsqueda en palabras (tokens)
        # Ejemplo: "jorge fu" -> ["jorge", "fu"]
        search_words = search.strip().split()
        
        if search_words:
            conditions = []
            for word in search_words:
                # Cada palabra debe estar presente en el nombre O en el email
                word_condition = or_(
                    User.full_name.ilike(f"%{word}%"),
                    User.email.ilike(f"%{word}%")
                )
                conditions.append(word_condition)
            
            # 2. Aplicamos todas las condiciones con un AND
            # Esto obliga a que la fila contenga TODAS las palabras buscadas
            query = query.filter(and_(*conditions))
    
    return query.offset(skip).limit(limit).all()

def create_user(db: Session, user: UserCreate):
    hashed_password = get_password_hash(user.password)
    db_user = User(
        email=user.email,
        full_name=user.full_name,
        hashed_password=hashed_password,
        role=user.role,
        is_active=user.is_active
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def update_user(db: Session, db_user: User, user_in: Union[UserUpdate, Dict[str, Any]]):
    if isinstance(user_in, dict):
        update_data = user_in
    else:
        update_data = user_in.model_dump(exclude_unset=True)

    # --- VALIDACIÓN DE EMAIL DUPLICADO ---
    if "email" in update_data and update_data["email"] != db_user.email:
        # Alguien más ya tiene este correo?
        email_exists = db.query(User).filter(User.email == update_data["email"]).first()
        if email_exists:
            raise HTTPException(
                status_code=400, 
                detail="El nuevo correo ya está registrado por otro usuario."
            )
    # -------------------------------------

    if "password" in update_data and update_data["password"]:
        update_data["hashed_password"] = get_password_hash(update_data["password"])
        del update_data["password"]

    for field in update_data:
        if hasattr(db_user, field):
            setattr(db_user, field, update_data[field])

    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user