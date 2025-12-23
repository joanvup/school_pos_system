from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session, joinedload
from app.db.session import get_db
from app.schemas.recharge import RechargeCreate, RechargeResponse
from app.crud import crud_transaction, crud_card
from app.api import deps
from app.models.user import User, UserRole
from app.utils.payu_service import PayUService
from app.models.card import Card, Transaction, TransactionType

router = APIRouter()

@router.get("/banks")
def get_pse_banks(current_user: User = Depends(deps.get_current_active_user)):
    """Retorna la lista de bancos de PayU"""
    banks = PayUService.get_banks()
    # Si por alguna razón la lista llega vacía, enviamos un error claro
    if not banks:
        raise HTTPException(
            status_code=503, 
            detail="No se pudo obtener la lista de bancos desde PayU. Verifique su conexión a internet o credenciales."
        )
    return banks

@router.post("/init-payu-pse")
def init_recharge(
    request: Request, # Recibir el objeto request
    payload: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.get_current_active_user)
):
    # --- 1. DETECTAR URL DINÁMICA ---
    # Usamos x-forwarded-proto para detectar si es HTTPS detrás de Nginx
    scheme = request.headers.get("x-forwarded-proto", "http")
    host = request.headers.get("host")
    base_url = f"{scheme}://{host}"
    
    client_ip = request.headers.get("X-Real-IP") or request.client.host
    user_agent = request.headers.get("User-Agent") or "Unknown"

    # --- 2. VALIDAR TARJETA ---
    card = db.query(Card).filter(Card.uid == payload['card_uid']).first()
    if not card: raise HTTPException(status_code=404, detail="Tarjeta no existe")

    # --- 3. LLAMAR A PAYU ---
    # Usamos el nombre del usuario logueado pero el email que viene del payload (editable)
    payload['buyer_name'] = current_user.full_name
    
    # El servicio PayU recibirá el email del payload, no forzado del user
    res, reference = PayUService.init_pse_payment(payload, client_ip, user_agent, base_url)

    tx_res = res.get("transactionResponse", {})
    state = tx_res.get("state")
    # LÓGICA DE VALIDACIÓN ROBUSTA
    if state == "PENDING" and "extraParameters" in tx_res and "BANK_URL" in tx_res["extraParameters"]:
        # EXTRAEMOS EL CUS (Trazability Code en PayU)
        cus = tx_res.get("trazabilityCode")
        # --- EL PAGO FUE ACEPTADO PARA REDIRECCIÓN ---
        new_tx = Transaction(
            card_id=card.id,
            amount=payload['amount'],
            type=TransactionType.RECHARGE,
            description=f"Recarga PSE en proceso ({reference})",
            reference_code=reference,
            cus=cus,
            status="pending"
        )
        db.add(new_tx)
        db.commit()

        return {
            "redirect_url": tx_res["extraParameters"]["BANK_URL"],
            "reference": reference
        }
    
    else:
        # --- EL PAGO FUE RECHAZADO O HUBO ERROR ---
        response_code = tx_res.get("responseCode", "UNKNOWN_ERROR")
        print(response_code)
        # Mapeo de errores comunes de PayU para el usuario
        error_msg = {
            "BANK_UNREACHABLE": "El simulador del banco no está disponible. Por favor selecciona 'BANCO UNION COLOMBIANO'.",
            "PAYMENT_NETWORK_BAD_RESPONSE": "Error de comunicación con la red de pagos.",
            "INVALID_SIGNATURE": "Error de seguridad en la firma de la transacción.",
            "EXCEEDED_AMOUNT": "El monto supera el límite permitido."
        }.get(response_code, f"Error en la transacción: {response_code}")

        raise HTTPException(status_code=400, detail=error_msg)

@router.post("/payu-confirmation")
async def payu_confirmation(request: Request, db: Session = Depends(get_db)):
    # 1. Capturar todo lo que llega
    try:
        raw_body = await request.form()
        form_data = dict(raw_body)
        print(f"--- WEBHOOK INCOMING ---")
        print(f"Payload: {form_data}")
    except Exception as e:
        print(f"ERROR: No se pudo leer el form de PayU: {e}")
        return {"message": "Invalid form"}

    # 2. Extraer datos con los nombres exactos de PayU
    merchant_id = form_data.get("merchant_id")
    reference = form_data.get("reference_sale")
    value = form_data.get("value")
    currency = form_data.get("currency")
    state = form_data.get("state_pol") # 4=Aprobado, 6=Rechazado
    incoming_sign = form_data.get("sign")
    cus = form_data.get("cus")

    # 3. Validar Firma
    if not PayUService.verify_confirmation_signature(merchant_id, reference, value, currency, state, incoming_sign):
        print(f"WEBHOOK ERROR: Firma inválida para ref {reference}")
        return {"message": "Invalid Signature"}

    # 4. Procesar en Base de Datos
    tx = db.query(Transaction).options(joinedload(Transaction.card))\
           .filter(Transaction.reference_code == reference).first()
           
    if not tx:
        print(f"WEBHOOK ERROR: Referencia {reference} no existe en DB local")
        return {"message": "TX Not Found"}

    if tx.status == "approved":
        return {"message": "Already Approved"}

    if state == "4": # APROBADO
        tx.status = "approved"
        tx.cus = cus
        tx.description = f"Recarga PSE Aprobada (CUS: {cus})"
        
        # ACTUALIZAR SALDO
        if tx.card:
            tx.card.balance += float(value)
            db.add(tx.card)
            db.commit()
            print(f"✅ SALDO ACTUALIZADO: Tarjeta {tx.card.uid} +${value}")
        else:
            print("ERROR: Transacción no tiene tarjeta asociada")
    else:
        tx.status = "declined"
        tx.description = f"Recarga PSE no aprobada. Estado PayU: {state}"
        db.commit()
        print(f"❌ TRANSACCIÓN RECHAZADA: Ref {reference}")

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