from sqlalchemy.orm import Session
from sqlalchemy import or_ 
from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate
from app.core.security import get_password_hash
from typing import Union, Dict, Any

def get_user_by_email(db: Session, email: str):
    return db.query(User).filter(User.email == email).first()

def get_users(db: Session, skip: int = 0, limit: int = 100, search: str = None):
    query = db.query(User)
    
    if search:
        search_fmt = f"%{search}%"
        # Busca si el string está en nombre O en email
        query = query.filter(
            or_(
                User.full_name.like(search_fmt), 
                User.email.like(search_fmt)
            )
        )
    
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
        update_data = user_in.dict(exclude_unset=True)
    
    if "password" in update_data and update_data["password"]:
        hashed_password = get_password_hash(update_data["password"])
        del update_data["password"]
        update_data["hashed_password"] = hashed_password
        
    for field in update_data:
        setattr(db_user, field, update_data[field])
        
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user