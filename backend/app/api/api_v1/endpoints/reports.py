from datetime import date
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import func, or_ # Importar 'or_' también es necesario para filtros cruzados
import io
import pandas as pd

from app.db.session import get_db
from app.crud import crud_report
from app.api import deps
from app.models.user import User
# --- ASEGÚRATE DE QUE ESTAS LÍNEAS DE ABAJO ESTÉN COMPLETAS ---
from app.models.card import Card, Transaction, TransactionType, TransactionDetail
from app.models.product import Product
from app.models.category import Category
# --------------------------------------------------------------
from app.utils.pdf_generator import generate_pdf_report

router = APIRouter()

# 1. DASHBOARD (Métricas rápidas)
@router.get("/dashboard")
def get_dashboard_metrics(
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.get_current_admin_or_supervisor)
):
    stats = crud_report.get_dashboard_stats(db)
    top_products = crud_report.get_top_selling_products(db)
    top_products_list = [{"name": p[0], "sold": float(p[1])} for p in top_products]
    return {"stats": stats, "top_products": top_products_list}

# 2. VISUALIZACIÓN POR PANTALLA (JSON filtrado)
@router.get("/sales-total", response_model=dict)
def read_sales_total(
    start_date: date = None,
    end_date: date = None,
    user_id: int = None,
    category_id: int = None,
    product_id: int = None,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.get_current_admin_or_supervisor)
):
    items, total = crud_report.get_sales_total_detailed(
        db, start_date, end_date, user_id, category_id, product_id, skip, limit
    )
    
    formatted_items = []
    for tx in items:
        comprador = "Desconocido"
        if tx.card:
            if tx.card.student:
                comprador = f"Est: {tx.card.student.full_name}"
            elif tx.card.employee:
                comprador = f"Emp: {tx.card.employee.full_name}"
            
        formatted_items.append({
            "id": tx.id,
            "timestamp": tx.timestamp,
            "comprador": comprador,
            "amount": abs(tx.amount),
            "reference": tx.reference_code,
            "details": [
                {
                    "product_name": d.product_name,
                    "quantity": d.quantity,
                    "unit_price": d.unit_price,
                    "subtotal": d.subtotal
                } for d in tx.details
            ]
        })
    return {"items": formatted_items, "total": total}

@router.get("/sales-by-product")
def read_sales_by_product(
    start_date: date = None,
    end_date: date = None,
    user_id: int = None,
    category_id: int = None,
    product_id: int = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.get_current_admin_or_supervisor)
):
    results = crud_report.get_sales_by_product_grouped(
        db, start_date, end_date, user_id, category_id, product_id
    )
    
    return [
        {
            "product": r.product_name,
            "category": r.category_name,
            "qty": r.total_qty,
            "total": r.total_revenue
        } for r in results
    ]

# 3. EXPORTACIÓN (Excel / PDF)
# backend/app/api/v1/endpoints/reports.py

@router.get("/export/{report_type}")
def export_report(
    report_type: str,
    format: str = Query("excel", regex="^(excel|pdf)$"),
    start_date: date = None,
    end_date: date = None,
    # --- CORRECCIÓN: Agregar estos parámetros que faltaban ---
    user_id: Optional[int] = None,
    category_id: Optional[int] = None,
    product_id: Optional[int] = None,
    # ---------------------------------------------------------
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.get_current_admin_or_supervisor)
):
    data = []
    headers = []
    title = f"Reporte: {report_type.upper().replace('_', ' ')}"
    filename = f"{report_type}_{start_date}_{end_date}"

    # 1. Reporte de Ventas Detalladas
    if report_type == "sales":
        raw, _ = crud_report.get_sales_total_detailed(
            db, start_date, end_date, user_id, category_id, product_id, limit=2000
        )
        headers = ["Fecha", "Comprador", "Monto", "Referencia"]
        for r in raw:
            comp = r.card.student.full_name if r.card.student else (r.card.employee.full_name if r.card.employee else "N/A")
            data.append([r.timestamp.strftime("%Y-%m-%d %H:%M"), comp, f"${abs(r.amount):,.0f}", r.reference_code or "-"])
        title = f"Ventas Totales ({start_date} a {end_date})"
    # 2. Reporte de Ventas por Producto (Agrupado)
    elif report_type == "sales_product":
        # Ahora estas variables sí existen porque están en los argumentos de la función
        raw = crud_report.get_sales_by_product_grouped(
            db, start_date, end_date, user_id, category_id, product_id
        )
        headers = ["Producto", "Categoría", "Cant. Vendida", "Total Recaudado"]
        data = [[r.product_name, r.category_name, r.total_qty, f"${r.total_revenue:,.0f}"] for r in raw]
        title = f"Ventas por Producto ({start_date} a {end_date})"
    # 3. Reporte de Inventario (Solo usa categoría y producto)
    elif report_type == "inventory":
        raw = crud_report.get_inventory_report_filtered(db, category_id, product_id)
        headers = ["Producto", "Categoría", "Stock", "Costo", "Precio", "Valoración"]
        data = [[r[0], r[1], r[2], f"${r[3]:,.0f}", f"${r[4]:,.0f}", f"${r[5]:,.0f}"] for r in raw]
        title = "Inventario Actual"
    # 4. Reporte de Recargas (Solo usa fecha)
    elif report_type == "recharges":
        raw = crud_report.get_recharges_report(db, start_date, end_date)
        headers = ["Fecha", "Ref. PSE", "CUS (Banco)", "Tarjeta UID", "Beneficiario", "Monto"]
        data = []
        for r in raw:
            ben = r.card.student.full_name if r.card.student else (r.card.employee.full_name if r.card.employee else "N/A")
            data.append([
                r.timestamp.strftime("%Y-%m-%d %H:%M"), 
                r.reference_code or "-", 
                r.cus or "-",
                r.card.uid, 
                ben, 
                f"${r.amount:,.0f}"
            ])
        title = f"Historial de Recargas PSE ({start_date} a {end_date})"
    # 5. Reporte de Balance (Solo usa fecha)
    elif report_type == "balance":
        # Usamos user_id como el ID de la tarjeta enviado desde el front
        if not user_id:
            raise HTTPException(status_code=400, detail="Debe seleccionar un usuario")
            
        card = db.query(Card).filter(Card.id == user_id).first()
        if not card:
            raise HTTPException(status_code=404, detail="Tarjeta no encontrada")
        
        # Obtener movimientos en el rango de fechas
        query = db.query(Transaction).filter(Transaction.card_id == card.id)
        if start_date:
            query = query.filter(func.date(Transaction.timestamp) >= start_date)
        if end_date:
            query = query.filter(func.date(Transaction.timestamp) <= end_date)
        
        raw_txs = query.order_by(Transaction.timestamp.asc()).all()
        
        # Titular
        nombre_titular = card.student.full_name if card.student else card.employee.full_name
        title = f"Extracto de Cuenta: {nombre_titular}\nSaldo Actual: ${card.balance:,.0f}"
        
        headers = ["Fecha", "Tipo", "Concepto", "Monto"]
        data = []
        for t in raw_txs:
            tipo = "RECARGA (+)" if t.type == "recharge" else "CONSUMO (-)"
            # Formatear monto con signo
            monto_str = f"${t.amount:,.0f}" if t.amount > 0 else f"-${abs(t.amount):,.0f}"
            
            data.append([
                t.timestamp.strftime("%Y-%m-%d %H:%M"),
                tipo,
                t.description or "Sin descripción",
                monto_str
            ])
        
        if not data:
            data = [["-", "-", "Sin movimientos en este periodo", "$0"]]
    # 6. Reporte de Entradas (Solo usa fecha)
    elif report_type == "orders":
        raw = crud_report.get_purchase_orders_report(db, start_date, end_date)
        headers = ["Fecha", "Código OC", "Responsable", "Estado", "Costo Total"]
        data = []
        for o in raw:
            data.append([
                o.timestamp.strftime("%Y-%m-%d %H:%M"),
                o.code,
                o.user.full_name,
                o.status.upper(),
                f"${o.total_cost:,.0f}"
            ])
        title = f"Reporte de Entradas de Almacén ({start_date} a {end_date})"
    # ... (Si no hay data, lanzamos error)
    if not data:
        raise HTTPException(status_code=404, detail="No hay datos para exportar")

    # 4. Generar el archivo
    if format == "pdf":
        pdf_buffer = generate_pdf_report(title, headers, data)
        return StreamingResponse(
            pdf_buffer, 
            media_type="application/pdf", 
            headers={"Content-Disposition": f"attachment; filename={filename}.pdf"}
        )
    else:
        df = pd.DataFrame(data, columns=headers)
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False)
        output.seek(0)
        return StreamingResponse(
            output, 
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename={filename}.xlsx"}
        )

@router.get("/inventory-status")
def read_inventory_status(
    category_id: Optional[int] = None,
    product_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.get_current_admin_or_supervisor)
):
    results = crud_report.get_inventory_report_filtered(db, category_id, product_id)
    
    return [
        {
            "name": r.product_name,
            "category": r.category_name,
            "stock": r.stock,
            "cost": r.cost,
            "price": r.price,
            "valuation": r.valuation
        } for r in results
    ]

@router.get("/recharges-history")
def read_recharges_history(
    start_date: date = None,
    end_date: date = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.get_current_admin_or_supervisor)
):
    results = crud_report.get_recharges_report(db, start_date, end_date)
    
    formatted = []
    for tx in results:
        beneficiario = "N/A"
        if tx.card.student:
            beneficiario = f"Est: {tx.card.student.full_name}"
        elif tx.card.employee:
            beneficiario = f"Emp: {tx.card.employee.full_name}"
            
        formatted.append({
            "id": tx.id,
            "timestamp": tx.timestamp,
            "uid": tx.card.uid,
            "beneficiario": beneficiario,
            "reference": tx.reference_code,
            "cus": tx.cus or "N/A", # <--- MOSTRAR CUS
            "amount": tx.amount
        })
    return formatted

@router.get("/student-balance/{card_id}")
def read_student_balance(
    card_id: int, # <--- Recibimos el ID de la tarjeta
    start_date: date = None,
    end_date: date = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.get_current_admin_or_supervisor)
):
    # Buscamos la tarjeta directamente
    card = db.query(Card).filter(Card.id == card_id).first()
    
    if not card:
        raise HTTPException(status_code=404, detail="Tarjeta no encontrada")

    # Obtenemos movimientos
    query = db.query(Transaction).filter(Transaction.card_id == card.id)
    if start_date: query = query.filter(func.date(Transaction.timestamp) >= start_date)
    if end_date: query = query.filter(func.date(Transaction.timestamp) <= end_date)
    
    txs = query.order_by(Transaction.timestamp.desc()).all()

    recharges = sum(t.amount for t in txs if t.type == TransactionType.RECHARGE)
    consumption = sum(abs(t.amount) for t in txs if t.type == TransactionType.PURCHASE)

    # El nombre depende de quién sea el dueño
    name = card.student.full_name if card.student else card.employee.full_name

    return {
        "student_name": name,
        "current_balance": card.balance,
        "summary": {
            "total_recharges": recharges,
            "total_consumption": consumption
        },
        "transactions": [
            {
                "id": t.id,
                "timestamp": t.timestamp,
                "type": t.type,
                "description": t.description,
                "amount": t.amount,
                "details": [{"product": d.product_name, "qty": d.quantity} for d in t.details]
            } for t in txs
        ]
    }

@router.get("/cardholders")
def get_all_cardholders(
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.get_current_admin_or_supervisor)
):
    """Retorna lista unificada de todos los que tienen tarjeta (Estudiantes y Empleados)"""
    # Buscamos en la tabla cards
    cards = db.query(Card).all()
    results = []
    for c in cards:
        name = ""
        tipo = ""
        if c.student:
            name = f"{c.student.full_name} (Est - {c.student.grade})"
            tipo = "student"
        elif c.employee:
            name = f"{c.employee.full_name} (Emp - {c.employee.role})"
            tipo = "employee"
            
        results.append({
            "card_id": c.id,
            "uid": c.uid,
            "display_name": name,
            "type": tipo
        })
    return results

@router.get("/purchase-orders-history")
def read_purchase_orders(
    start_date: date = None,
    end_date: date = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.get_current_admin_or_supervisor)
):
    orders = crud_report.get_purchase_orders_report(db, start_date, end_date)
    
    return [
        {
            "id": o.id,
            "code": o.code,
            "timestamp": o.timestamp,
            "user_name": o.user.full_name,
            "total_cost": o.total_cost,
            "status": o.status,
            "details": [
                {
                    "product": d.product.name,
                    "qty": d.quantity,
                    "cost": d.unit_cost,
                    "subtotal": d.quantity * d.unit_cost
                } for d in o.details
            ]
        } for o in orders
    ]