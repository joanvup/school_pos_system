from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.student import StudentCreate, StudentResponse, StudentUpdate
from app.crud import crud_student, crud_user
from app.api import deps
from app.models.user import User, UserRole

router = APIRouter()

@router.post("/", response_model=StudentResponse)
def create_student_admin(
    student: StudentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.get_current_active_admin)
):
    """
    ADMIN: Crear estudiante y asignarlo a un padre existente.
    """
    # Verificar si el padre existe
    parent = crud_user.get_user_by_email(db, email="") # Hack para buscar por ID no implementado en crud_user
    # Mejor busquemos el padre directamente en la DB aqui por simplicidad o agregamos get_user_by_id en crud_user
    # Vamos a asumir que el ID enviado es correcto o fallará por Foreign Key, 
    # pero para mejor UX verificamos:
    parent_user = db.query(User).filter(User.id == student.parent_id).first()
    if not parent_user:
        raise HTTPException(status_code=404, detail="El ID del padre no existe")
    
    return crud_student.create_student(db=db, student=student)

@router.get("/me", response_model=List[StudentResponse])
def read_my_students(
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.get_current_active_user)
):
    """
    PADRE: Ver mis hijos asignados.
    """
    return crud_student.get_students_by_parent(db, parent_id=current_user.id)

@router.get("/", response_model=List[StudentResponse])
def read_all_students(
    skip: int = 0,
    limit: int = 20,
    search: Optional[str] = None, # Nuevo
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.get_current_active_admin)
):
    return crud_student.get_students(db, skip=skip, limit=limit, search=search)