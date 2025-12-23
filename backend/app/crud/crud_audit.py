from sqlalchemy.orm import Session
from app.models.card import AuditLog

def log_action(db: Session, user_id: int, action: str, details: str):
    """
    Registra una acción en la tabla de auditoría.
    Ej: User 1 (Admin) ACTION: UPDATE_CARD DETAILS: Bloqueó tarjeta ABC
    """
    try:
        log = AuditLog(
            user_id=user_id,
            action=action,
            details=details
        )
        db.add(log)
        db.commit()
    except Exception as e:
        # Si falla el log, no deberíamos detener la operación principal, 
        # pero sí imprimirlo en consola.
        print(f"ERROR AUDITORIA: {e}")