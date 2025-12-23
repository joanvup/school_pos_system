from sqlalchemy.orm import Session, joinedload
from app.models.card import Card, CardStatus
from app.schemas.card import CardCreate, CardUpdate
from app.models.card import AuditLog


def get_card_by_uid(db: Session, uid: str):
    # Agregamos options(joinedload(...)) para que la consulta traiga al dueño
    return db.query(Card).options(
        joinedload(Card.student),
        joinedload(Card.employee)
    ).filter(Card.uid == uid).first()

def get_card_by_student(db: Session, student_id: int):
    return db.query(Card).filter(Card.student_id == student_id).first()

def create_card(db: Session, card: CardCreate):
    # Verificar si el estudiante ya tiene tarjeta activa y bloquearla? 
    # Por ahora asumimos que no tiene o el frontend valida.
    db_card = Card(
        uid=card.uid,
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
    
    for key, value in update_data.items():
        setattr(db_card, key, value)
    
    db.add(db_card)
    db.commit()
    db.refresh(db_card)
    return db_card

def replace_card_uid(db: Session, current_card: Card, new_uid: str, actor_id: int):
    """
    Cambia el UID físico de una tarjeta manteniendo el saldo y el historial.
    """
    # 1. Verificar si el NUEVO UID ya existe en el sistema
    exists = db.query(Card).filter(Card.uid == new_uid).first()
    if exists:
        return None, "La nueva tarjeta ya está asignada a otra persona."

    old_uid = current_card.uid
    
    # 2. Actualizar el UID
    current_card.uid = new_uid
    current_card.status = "active" # La activamos automáticamente al ser nueva
    
    # 3. Registrar en Auditoría
    details = f"Reemplazo de tarjeta. Antigua: {old_uid} -> Nueva: {new_uid}. Saldo preservado: {current_card.balance}"
    audit = AuditLog(user_id=actor_id, action="REPLACE_CARD", details=details)
    
    db.add(audit)
    db.commit()
    db.refresh(current_card)
    return current_card, None