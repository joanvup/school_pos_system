from sqlalchemy import func, or_, desc
from app.models.card import Transaction, TransactionDetail, TransactionType, Card
from app.models.product import Product
from app.models.category import Category
from app.models.purchase import PurchaseOrderDetail
from app.models.user import User, Student
from sqlalchemy.orm import Session 
from datetime import datetime, time

def get_sales_total_detailed(
    db: Session, 
    start_date=None, 
    end_date=None, 
    user_id=None, 
    category_id=None, 
    product_id=None,
    skip=0,
    limit=50
):
    # Base de la consulta: Compras (PURCHASE)
    query = db.query(Transaction).join(Card, Transaction.card_id == Card.id).filter(
        Transaction.type == TransactionType.PURCHASE
    )

    # Filtro de Fechas
    if start_date:
        query = query.filter(func.date(Transaction.timestamp) >= start_date)
    if end_date:
        query = query.filter(func.date(Transaction.timestamp) <= end_date)

    # Filtro de Usuario (Dueño de la tarjeta: Estudiante o Empleado)
    if user_id:
        # Buscamos transacciones donde la tarjeta pertenezca al usuario (empleado) 
        # o a un estudiante vinculado a ese usuario (padre)
        query = query.outerjoin(Student, Card.student_id == Student.id).filter(
            or_(Card.user_id == user_id, Student.parent_id == user_id)
        )

    # Filtros por Producto o Categoría (requiere join con detalles)
    if category_id or product_id:
        query = query.join(TransactionDetail, Transaction.id == TransactionDetail.transaction_id)\
                     .join(Product, TransactionDetail.product_id == Product.id)
        
        if category_id:
            query = query.filter(Product.category_id == category_id)
        if product_id:
            query = query.filter(Product.id == product_id)

    # Ordenar por lo más reciente
    query = query.order_by(Transaction.timestamp.desc())

    total = query.count()
    results = query.offset(skip).limit(limit).all()
    
    return results, total

def get_sales_by_product_grouped(
    db: Session, 
    start_date=None, 
    end_date=None, 
    user_id=None, 
    category_id=None, 
    product_id=None
):
    # Usamos TransactionDetail como base
    query = db.query(
        Product.name.label("product_name"),
        Category.name.label("category_name"),
        func.sum(TransactionDetail.quantity).label("total_qty"),
        func.sum(TransactionDetail.subtotal).label("total_revenue")
    ).join(Product, TransactionDetail.product_id == Product.id) \
     .join(Category, Product.category_id == Category.id) \
     .join(Transaction, TransactionDetail.transaction_id == Transaction.id) \
     .join(Card, Transaction.card_id == Card.id)

    # Filtro Obligatorio: Solo Compras
    query = query.filter(Transaction.type == TransactionType.PURCHASE)

    # Filtro de Fechas (Aseguramos que se traten como fechas de MySQL)
    if start_date:
        query = query.filter(func.date(Transaction.timestamp) >= start_date)
    if end_date:
        query = query.filter(func.date(Transaction.timestamp) <= end_date)
    
    # Filtros Opcionales
    if category_id:
        query = query.filter(Product.category_id == category_id)
    if product_id:
        query = query.filter(Product.id == product_id)
        
    if user_id:
        # Join con Student para buscar por ID de Padre si aplica
        query = query.outerjoin(Student, Card.student_id == Student.id).filter(
            or_(
                Card.user_id == user_id,       # Caso Empleado
                Student.parent_id == user_id   # Caso Padre/Hijo
            )
        )

    # AGRUPACIÓN Y ORDEN
    query = query.group_by(Product.name, Category.name).order_by(desc("total_revenue"))
    
    return query.all()

def get_inventory_report_filtered(db: Session, category_id=None, product_id=None):
    # Base de la consulta con Joins
    query = db.query(
        Product.name.label("product_name"),
        Category.name.label("category_name"),
        Product.stock,
        Product.cost,
        Product.price,
        (Product.stock * Product.cost).label("valuation")
    ).join(Category, Product.category_id == Category.id)

    # Filtros
    if category_id:
        query = query.filter(Product.category_id == category_id)
    if product_id:
        query = query.filter(Product.id == product_id)

    # Ordenar por categoría y luego nombre
    query = query.order_by(Category.name, Product.name)
    
    return query.all()

def get_recharges_report(db: Session, start_date=None, end_date=None):
    # Base: Transacciones de tipo RECHARGE
    query = db.query(Transaction).join(Card, Transaction.card_id == Card.id).filter(
        Transaction.type == TransactionType.RECHARGE
    )

    # Filtros de fecha
    if start_date:
        query = query.filter(func.date(Transaction.timestamp) >= start_date)
    if end_date:
        query = query.filter(func.date(Transaction.timestamp) <= end_date)

    # Ordenar por lo más reciente
    query = query.order_by(Transaction.timestamp.desc())
    
    return query.all()

def get_student_balance_data(db: Session, student_id: int, start_date=None, end_date=None):
    # Buscamos la tarjeta del estudiante
    card = db.query(Card).filter(Card.student_id == student_id).first()
    if not card:
        return None, [], 0, 0

    # Base: Todas las transacciones de esa tarjeta
    query = db.query(Transaction).filter(Transaction.card_id == card.id)

    if start_date:
        query = query.filter(func.date(Transaction.timestamp) >= start_date)
    if end_date:
        query = query.filter(func.date(Transaction.timestamp) <= end_date)

    # Ordenar por fecha ascendente para ver el flujo cronológico
    transactions = query.order_by(Transaction.timestamp.asc()).all()

    # Calcular resúmenes
    total_recharges = sum(t.amount for t in transactions if t.type == TransactionType.RECHARGE)
    total_consumption = sum(abs(t.amount) for t in transactions if t.type == TransactionType.PURCHASE)

    return card, transactions, total_recharges, total_consumption

from app.models.purchase import PurchaseOrder

def get_purchase_orders_report(db: Session, start_date=None, end_date=None):
    query = db.query(PurchaseOrder).join(User, PurchaseOrder.user_id == User.id)

    if start_date:
        query = query.filter(func.date(PurchaseOrder.timestamp) >= start_date)
    if end_date:
        query = query.filter(func.date(PurchaseOrder.timestamp) <= end_date)

    return query.order_by(PurchaseOrder.timestamp.desc()).all()

def get_dashboard_stats(db: Session):
    """
    Obtiene métricas para el dashboard con filtros de fecha robustos.
    """
    # 1. Definir el inicio y fin de HOY con precisión
    today_start = datetime.combine(datetime.now().date(), time.min) # 2025-12-20 00:00:00
    today_end = datetime.combine(datetime.now().date(), time.max)   # 2025-12-20 23:59:59
    
    # 2. Total Ventas Hoy
    # Usamos Transaction.timestamp.between para mayor precisión y compatibilidad de índices
    sales_today = db.query(func.sum(Transaction.amount)).filter(
        Transaction.type == TransactionType.PURCHASE,
        Transaction.timestamp >= today_start,
        Transaction.timestamp <= today_end
    ).scalar() or 0.0

    # 3. Cantidad de Transacciones Hoy
    tx_count_today = db.query(func.count(Transaction.id)).filter(
        Transaction.type == TransactionType.PURCHASE,
        Transaction.timestamp >= today_start,
        Transaction.timestamp <= today_end
    ).scalar() or 0

    # 4. Productos con Stock Bajo
    low_stock_count = db.query(func.count(Product.id)).filter(
        Product.is_active == True,
        Product.stock <= Product.low_stock_threshold
    ).scalar() or 0

    # 5. Total Usuarios
    total_users = db.query(func.count(User.id)).scalar() or 0

    return {
        "sales_today": abs(float(sales_today)), # Aseguramos que sea positivo y float
        "transactions_today": int(tx_count_today),
        "low_stock_alert": int(low_stock_count),
        "total_users": int(total_users)
    }

def get_top_selling_products(db: Session, limit: int = 5):
    """
    Top productos más vendidos históricamente.
    """
    return db.query(
        TransactionDetail.product_name,
        func.sum(TransactionDetail.quantity).label("total_sold")
    ).group_by(
        TransactionDetail.product_name
    ).order_by(
        desc("total_sold")
    ).limit(limit).all()