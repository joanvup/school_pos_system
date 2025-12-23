from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.schemas.recharge import RechargeCreate, RechargeResponse
from app.crud import crud_transaction, crud_card
from app.api import deps
from app.models.user import User, UserRole
from app.utils.payu_service import PayUService
from app.models.card import Card

router = APIRouter()

@router.get("/banks")
def get_pse_banks(current_user: User = Depends(deps.get_current_active_user)):
    """Retorna la lista de bancos de PayU"""
    return PayUService.get_banks()

@router.post("/init-payu-pse")
def init_recharge(
    payload: dict, # amount, bank_code, user_type, card_uid, etc.
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.get_current_active_user)
):
    # 1. Buscar la tarjeta
    card = db.query(Card).filter(Card.uid == payload['card_uid']).first()
    if not card: raise HTTPException(status_code=404, detail="Tarjeta no existe")

    # 1. Preparar datos adicionales
    payload['buyer_email'] = current_user.email
    payload['buyer_name'] = current_user.full_name
    
    # 2. Llamar a PayU
    res, reference = PayUService.init_pse_payment(payload)
    
    if res.get("status") == "SUCCESS":
        # Guardamos la transacción con estado 'PENDING'
        # Debes crear el registro en la tabla transactions aquí
        # --- NUEVO: GUARDAR TRANSACCIÓN PENDIENTE ---
        new_tx = Transaction(
            card_id=card.id,
            amount=payload['amount'],
            type=TransactionType.RECHARGE,
            description=f"Recarga PSE en proceso",
            reference_code=reference,
            status="pending" # Importante
        )
        db.add(new_tx)
        db.commit()
        # --------------------------------------------
        return {
            "redirect_url": res["transactionResponse"]["extraParameters"]["BANK_URL"],
            "reference": reference
        }
    else:
        raise HTTPException(status_code=400, detail=res.get("transactionResponse", {}).get("paymentNetworkResponseErrorMessage", "Error en PayU"))

@router.post("/payu-confirmation")
async def payu_confirmation(request: Request, db: Session = Depends(get_db)):
    """
    Este es el Webhook. PayU lo llama por debajo.
    """
    # 1. Obtener datos de PayU (vienen como Form Data)
    form_data = await request.form()
    
    merchant_id = form_data.get("merchant_id")
    reference = form_data.get("reference_sale")
    value = form_data.get("value")
    currency = form_data.get("currency")
    state = form_data.get("state_pol") # 4=Aprobado, 6=Rechazado
    incoming_sign = form_data.get("sign")

    # 2. Validar Firma
    if not PayUService.verify_confirmation_signature(merchant_id, reference, value, currency, state, incoming_sign):
        return {"message": "Firma inválida"}

    # 3. Buscar la transacción en nuestra DB
    tx = db.query(Transaction).filter(Transaction.reference_code == reference).first()
    if not tx:
        return {"message": "Referencia no encontrada"}

    # 4. Si ya fue procesada, ignorar (PayU a veces envía varios avisos)
    if tx.status == "approved":
        return {"message": "Ya procesada"}

    # 5. Procesar según el estado de PayU
    if state == "4": # APROBADO
        tx.status = "approved"
        tx.description = f"Recarga PSE exitosa (Ref: {form_data.get('transaction_id')})"
        
        # SUMAR SALDO A LA TARJETA
        tx.card.balance += float(value)
        db.add(tx.card)
        
    elif state == "6": # RECHAZADO
        tx.status = "declined"
        tx.description = "Recarga PSE rechazada por el banco"
    
    elif state == "5": # EXPIRADO
        tx.status = "expired"
        tx.description = "Recarga PSE expirada (no pagó)"

    db.commit()
    return {"message": "OK"}

@router.get("/status/{reference_code}")
def get_recharge_status(reference_code: str, db: Session = Depends(get_db)):
    """Consultar el estado de una recarga específica en nuestra DB"""
    tx = db.query(Transaction).filter(Transaction.reference_code == reference_code).first()
    if not tx:
        raise HTTPException(status_code=404, detail="Transacción no encontrada")
    
    return {
        "status": tx.status, # pending, approved, declined
        "amount": tx.amount,
        "timestamp": tx.timestamp
    }

@router.post("/simulate-pse", response_model=RechargeResponse)
def simulate_pse_recharge(
    recharge: RechargeCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.get_current_active_user)
):
    """
    Simula una transacción aprobada por PSE.
    Validaciones:
    - Admin: Puede recargar cualquiera.
    - Empleado: Solo su propia tarjeta.
    - Padre: Solo tarjetas de sus hijos.
    """
    
    # 1. Obtener la tarjeta para validar permisos
    card = crud_card.get_card_by_uid(db, uid=recharge.card_uid)
    if not card:
        raise HTTPException(status_code=404, detail="Tarjeta no encontrada")

    # 2. Validar Permisos
    is_authorized = False

    if current_user.role == UserRole.ADMIN:
        is_authorized = True
    
    elif current_user.role == UserRole.EMPLEADO:
        # Verificar si la tarjeta es del empleado
        if card.user_id == current_user.id:
            is_authorized = True
            
    elif current_user.role == UserRole.PADRE:
        # Verificar si la tarjeta pertenece a un estudiante de este padre
        if card.student and card.student.parent_id == current_user.id:
            is_authorized = True

    if not is_authorized:
        raise HTTPException(
            status_code=403, 
            detail="No tienes permiso para recargar esta tarjeta."
        )

    # 3. Procesar Recarga
    return crud_transaction.recharge_card(db=db, recharge=recharge)