from sqlalchemy.orm import Session
from fastapi import HTTPException
from app.models.category import Category
from app.models.product import Product
from app.schemas.category import CategoryCreate

def get_categories(db: Session, skip: int = 0, limit: int = 100):
    return db.query(Category).offset(skip).limit(limit).all()

def create_category(db: Session, category: CategoryCreate):
    db_obj = Category(name=category.name)
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj

def update_category(db: Session, category_id: int, name: str):
    db_cat = db.query(Category).filter(Category.id == category_id).first()
    if not db_cat:
        raise HTTPException(status_code=404, detail="Categoría no encontrada")
    db_cat.name = name
    db.commit()
    db.refresh(db_cat)
    return db_cat

def delete_category(db: Session, category_id: int):
    # 1. Validación de Integridad
    products_count = db.query(Product).filter(Product.category_id == category_id).count()
    if products_count > 0:
        raise HTTPException(
            status_code=400, 
            detail=f"No se puede eliminar: Hay {products_count} productos asociados a esta categoría."
        )

    # 2. Eliminar
    db_cat = db.query(Category).filter(Category.id == category_id).first()
    if not db_cat:
        raise HTTPException(status_code=404, detail="Categoría no encontrada")
    
    db.delete(db_cat)
    db.commit()
    return {"message": "Categoría eliminada"}