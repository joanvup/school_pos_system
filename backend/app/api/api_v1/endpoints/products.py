from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.product import ProductCreate, ProductResponse, ProductUpdate
from app.crud import crud_product
from app.api import deps
from app.models.user import User
from app.models.product import Product
from app.core.config import settings
from app.utils.images import store_image

from fastapi import UploadFile, File

router = APIRouter()

@router.post("/", response_model=ProductResponse)
def create_product(
    product: ProductCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.get_current_active_admin) # Solo Admin crea
):
    """
    Crear un nuevo producto en el inventario.
    """
    return crud_product.create_product(db=db, product=product)

@router.get("/", response_model=List[ProductResponse])
def read_products(
    skip: int = 0,
    limit: int = 100,
    category: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.get_current_active_user) # Vendedores y Admins ven
):
    """
    Listar productos disponibles para la venta.
    """
    return crud_product.get_products(db, skip=skip, limit=limit, category=category)

@router.get("/low-stock", response_model=List[ProductResponse])
def read_low_stock_products(
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.get_current_active_admin) # Alerta administrativa
):
    """
    Obtener lista de productos con stock crítico.
    """
    return crud_product.get_low_stock_products(db)

@router.put("/{product_id}", response_model=ProductResponse)
def update_product(
    product_id: int,
    product_in: ProductUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.get_current_admin_or_supervisor)
):
    """
    Actualizar stock, precio o detalles de un producto.
    """
    product = crud_product.get_product(db, product_id=product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    
    return crud_product.update_product(db, db_product=product, product_in=product_in)

@router.delete("/{product_id}")
def delete_existing_product(
    product_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.get_current_active_admin)
):
    """Eliminar producto si no tiene historial"""
    return crud_product.delete_product(db, product_id)

@router.post("/{product_id}/image")
async def upload_product_image(
    product_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.get_current_admin_or_supervisor)
):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Producto no encontrado")

    image_url = await store_image(
        file,
        subdir="products",
        prefix=f"product-{product_id}",
        max_bytes=settings.MAX_UPLOAD_BYTES,
    )

    product.image_url = image_url
    db.commit()

    return {"image_url": product.image_url}