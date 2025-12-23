from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db, SessionLocal
from app.api import deps
from app.models.user import User
from app.utils.excel_handler import process_students_file, process_employees_file 
from app.utils import excel_handler

router = APIRouter()


@router.post("/students", status_code=200)
async def import_students_excel(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.get_current_active_admin) # Solo Admin
):
    """
    Carga masiva de estudiantes y padres desde Excel (.xlsx).
    Columnas esperadas: student_name, grade, parent_name, parent_email
    """
    if not file.filename.endswith('.xlsx'):
        raise HTTPException(status_code=400, detail="El archivo debe ser un Excel (.xlsx)")

    contents = await file.read()
    results = process_students_file(contents, db)
    
    if "error" in results:
        raise HTTPException(status_code=400, detail=results["error"])
        
    return results

@router.post("/employees", status_code=200)
async def import_employees_excel(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.get_current_active_admin)
):
    """
    Carga masiva de empleados desde Excel.
    Columnas: full_name, email, password (opcional)
    """
    if not file.filename.endswith('.xlsx'):
        raise HTTPException(status_code=400, detail="El archivo debe ser .xlsx")

    contents = await file.read()
    results = process_employees_file(contents, db)
    
    if "error" in results:
        raise HTTPException(status_code=400, detail=results["error"])
        
    return results