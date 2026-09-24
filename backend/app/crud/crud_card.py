from sqlalchemy.orm import Session, joinedload
from app.models.card import Card, CardStatus
from app.schemas.card import CardCreate, CardUpdate
from app.models.card import AuditLog

def normalize_card_uid(uid: str) -> str:
    if not uid:
        return ""
    return str(uid).strip().replace(":", "").replace("-", "").replace(" ", "").upper()

def get_card_by_uid(db: Session, uid: str):
    clean_uid = normalize_card_uid(uid)
    return db.query(Card).options(
        joinedload(Card.student),
        joinedload(Card.employee)
    ).filter(Card.uid == clean_uid).first()

def get_card_by_student(db: Session, student_id: int):
    return db.query(Card).filter(Card.student_id == student_id).first()

def create_card(db: Session, card: CardCreate):
    clean_uid = normalize_card_uid(card.uid)
    db_card = Card(
        uid=clean_uid,
        student_id=card.student_id,
        user_id=card.user_id,
        balance=0.0, # Saldo inicial siempre 0
        status=CardStatus.ACTIVE,
        daily_limit=card.daily_limit
    )
    db.add(db_card)
    db.commit()
    db.refresh(db_card)
    return db_card

def update_card(db: Session, db_card: Card, card_in: CardUpdate):
    update_data = card_in.dict(exclude_unset=True)
    if "uid" in update_data and update_data["uid"]:
        update_data["uid"] = normalize_card_uid(update_data["uid"])
        
    for key, value in update_data.items():
        setattr(db_card, key, value)
    
    db.add(db_card)
    db.commit()
    db.refresh(db_card)
    return db_card

def replace_card_uid(db: Session, current_card: Card, new_uid: str, actor_id: int):
    """
    Cambia el UID físico de una tarjeta NFC manteniendo el saldo y el historial.
    """
    clean_new_uid = normalize_card_uid(new_uid)
    # 1. Verificar si el NUEVO UID ya existe en el sistema
    exists = db.query(Card).filter(Card.uid == clean_new_uid).first()
    if exists:
        return None, "La nueva tarjeta ya está asignada a otra persona."

    old_uid = current_card.uid
    
    # 2. Actualizar el UID
    current_card.uid = clean_new_uid
    current_card.status = "active" # La activamos automáticamente al ser nueva
    
    # 3. Registrar en Auditoría
    details = f"Reemplazo de tarjeta NFC. Antigua: {old_uid} -> Nueva: {clean_new_uid}. Saldo preservado: {current_card.balance}"
    audit = AuditLog(user_id=actor_id, action="REPLACE_CARD", details=details)
    
    db.add(audit)
    db.commit()
    db.refresh(current_card)
    return current_card, None

def unlink_card(db: Session, card: Card, actor_id: int):
    """
    Desvincula una tarjeta NFC de su dueño (estudiante o empleado).
    La tarjeta queda bloqueada pero conserva su saldo e historial.
    """
    owner = None
    if card.student:
        owner = f"Estudiante: {card.student.full_name}"
    elif card.employee:
        owner = f"Empleado: {card.employee.full_name}"

    card.student_id = None
    card.user_id = None
    card.status = CardStatus.BLOCKED

    # Registrar en Auditoría
    details = f"Desvinculación de tarjeta NFC UID {card.uid}. Dueño anterior: {owner or 'Desconocido'}. Saldo conservado: {card.balance}"
    audit = AuditLog(user_id=actor_id, action="UNLINK_CARD", details=details)

    db.add(audit)
    db.commit()
    db.refresh(card)
    return card

def relink_card(db: Session, db_card: Card, student_id, user_id, daily_limit, actor_id):
    """
    Re-vincula una tarjeta NFC previamente desvinculada a un estudiante o empleado.
    La reactiva y conserva su saldo e historial.
    """
    owner = None
    if student_id:
        db_card.student_id = student_id
        db_card.user_id = None  # Una tarjeta pertenece a UN solo dueño
        owner = f"Estudiante ID {student_id}"
    elif user_id:
        db_card.user_id = user_id
        db_card.student_id = None
        owner = f"Empleado ID {user_id}"

    db_card.status = CardStatus.ACTIVE
    if daily_limit is not None:
        db_card.daily_limit = daily_limit

    # Registrar en Auditoría
    details = f"Re-vinculación de tarjeta NFC UID {db_card.uid} a {owner or 'Desconocido'}. Saldo conservado: {db_card.balance}"
    audit = AuditLog(user_id=actor_id, action="LINK_CARD", details=details)

    db.add(audit)
    db.commit()
    db.refresh(db_card)
    return db_card