from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.schemas.category import CategoryCreate, CategoryResponse
from app.crud import crud_category
from app.api import deps
from app.models.user import User

router = APIRouter()

@router.get("/", response_model=List[CategoryResponse])
def read_categories(db: Session = Depends(get_db)):
    return crud_category.get_categories(db)

@router.post("/", response_model=CategoryResponse)
def create_category(
    category: CategoryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.get_current_active_admin)
):
    return crud_category.create_category(db, category)

@router.put("/{cat_id}", response_model=CategoryResponse)
def update_category(
    cat_id: int,
    category: CategoryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.get_current_active_admin)
):
    return crud_category.update_category(db, cat_id, category.name)

@router.delete("/{cat_id}")
def delete_category(
    cat_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.get_current_active_admin)
):
    return crud_category.delete_category(db, cat_id)