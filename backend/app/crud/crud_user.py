from typing import Any, Dict, Union

from fastapi import HTTPException
from sqlalchemy import and_, func, or_
from sqlalchemy.orm import Session

from app.core.security import get_password_hash
from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate


def normalize_email(email: str) -> str:
    return (email or "").strip().lower()


def get_user_by_email(db: Session, email: str):
    normalized = normalize_email(email)
    if not normalized:
        return None
    return (
        db.query(User)
        .filter(func.lower(User.email) == normalized)
        .first()
    )


def get_user_by_id(db: Session, user_id: int):
    return db.query(User).filter(User.id == user_id).first()


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
                    User.email.ilike(f"%{word}%"),
                )
                conditions.append(word_condition)

            # 2. Aplicamos todas las condiciones con un AND
            # Esto obliga a que la fila contenga TODAS las palabras buscadas
            query = query.filter(and_(*conditions))

    return query.offset(skip).limit(limit).all()


def create_user(db: Session, user: UserCreate):
    hashed_password = get_password_hash(user.password)
    db_user = User(
        email=normalize_email(str(user.email)),
        full_name=user.full_name,
        hashed_password=hashed_password,
        role=user.role,
        is_active=user.is_active,
        must_change_password=False,
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


def update_user(
    db: Session,
    db_user: User,
    user_in: Union[UserUpdate, Dict[str, Any]],
    force_password_change: bool = False,
):
    if isinstance(user_in, dict):
        update_data = dict(user_in)
    else:
        update_data = user_in.model_dump(exclude_unset=True)

    # --- VALIDACIÓN DE EMAIL DUPLICADO ---
    if "email" in update_data and update_data["email"]:
        update_data["email"] = normalize_email(str(update_data["email"]))
        if update_data["email"] != normalize_email(db_user.email):
            email_exists = (
                db.query(User)
                .filter(func.lower(User.email) == update_data["email"])
                .first()
            )
            if email_exists:
                raise HTTPException(
                    status_code=400,
                    detail="El nuevo correo ya está registrado por otro usuario.",
                )
    # -------------------------------------

    revoke_tokens = False

    if update_data.get("password"):
        update_data["hashed_password"] = get_password_hash(update_data["password"])
        update_data["must_change_password"] = force_password_change
        update_data["failed_login_attempts"] = 0
        update_data["locked_until"] = None
        revoke_tokens = True
        del update_data["password"]

    if (
        "is_active" in update_data
        and update_data["is_active"] is False
        and db_user.is_active
    ):
        revoke_tokens = True

    if revoke_tokens:
        update_data["token_version"] = (db_user.token_version or 0) + 1

    for field in update_data:
        if hasattr(db_user, field):
            setattr(db_user, field, update_data[field])

    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user
