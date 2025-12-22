from app.models.product import Product
from app.schemas.product import ProductCreate, ProductUpdate
from sqlalchemy.orm import Session, joinedload
from app.models.card import TransactionDetail
from app.models.purchase import PurchaseOrderDetail
from fastapi import HTTPException
from app.models.category import Category 

def get_product(db: Session, product_id: int):
    return db.query(Product).filter(Product.id == product_id).first()

#def get_products(db: Session, skip: int = 0, limit: int = 100):
#    return db.query(Product)\
#        .options(joinedload(Product.category_rel))\
#        .filter(Product.is_active == True)\
#        .offset(skip).limit(limit).all()
def get_products(db: Session, skip: int = 0, limit: int = 100):
    # 1. Usamos joinedload para traer la categoría en una sola consulta
    # 2. Ordenamos por el nombre de la categoría y luego por el nombre del producto
    return db.query(Product)\
        .join(Category)\
        .options(joinedload(Product.category_rel))\
        .filter(Product.is_active == True)\
        .order_by(Category.name.asc(), Product.name.asc())\
        .offset(skip).limit(limit).all()
        
def get_products(db: Session, skip: int = 0, limit: int = 100, category: str = None):
    query = db.query(Product)
    if category:
        query = query.filter(Product.category == category)
    return query.filter(Product.is_active == True).offset(skip).limit(limit).all()


def get_low_stock_products(db: Session):
    """Retorna productos cuyo stock es menor o igual al umbral definido"""
    return db.query(Product).filter(
        Product.is_active == True,
        Product.stock <= Product.low_stock_threshold
    ).all()

def create_product(db: Session, product: ProductCreate):
    db_product = Product(
        name=product.name,
        description=product.description,
        category_id=product.category_id,
        price=product.price,
        cost=product.cost,
        stock=0,
        low_stock_threshold=product.low_stock_threshold,
        image_url=product.image_url,
        is_active=product.is_active
    )
    db.add(db_product)
    db.commit()
    db.refresh(db_product)
    return db_product

def update_product(db: Session, db_product: Product, product_in: ProductUpdate):
    update_data = product_in.dict(exclude_unset=True)
    for field in update_data:
        setattr(db_product, field, update_data[field])
    
    db.add(db_product)
    db.commit()
    db.refresh(db_product)
    return db_product

def delete_product(db: Session, product_id: int):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Producto no encontrado")

    # 1. Validar movimientos en Ventas
    sales_count = db.query(TransactionDetail).filter(TransactionDetail.product_id == product_id).count()
    if sales_count > 0:
        raise HTTPException(
            status_code=400, 
            detail=f"No se puede eliminar: El producto tiene {sales_count} registros de venta asociados. Considere desactivarlo en su lugar."
        )

    # 2. Validar movimientos en Órdenes de Compra (Entradas)
    purchases_count = db.query(PurchaseOrderDetail).filter(PurchaseOrderDetail.product_id == product_id).count()
    if purchases_count > 0:
        raise HTTPException(
            status_code=400, 
            detail=f"No se puede eliminar: El producto tiene {purchases_count} registros de entrada al almacén."
        )

    # 3. Si no tiene movimientos, eliminar
    db.delete(product)
    db.commit()
    return {"message": "Producto eliminado exitosamente"}