import os
import shutil
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.api import deps
from app.models.setting import SystemSetting
from app.models.user import User

router = APIRouter()

@router.get("/")
def get_all_settings(db: Session = Depends(get_db)):
    """Obtener todas las configuraciones públicas"""
    settings = db.query(SystemSetting).all()
    # Convertimos a un diccionario simple para el frontend
    return {s.key: s.value for s in settings}

@router.put("/")
def update_settings(
    payload: dict, # Recibe {key: value}
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.get_current_active_admin) # Solo Admin
):
    """Actualizar múltiples parámetros de configuración"""
    for key, value in payload.items():
        db_setting = db.query(SystemSetting).filter(SystemSetting.key == key).first()
        if db_setting:
            db_setting.value = str(value)
        else:
            new_setting = SystemSetting(key=key, value=str(value))
            db.add(new_setting)
    
    db.commit()
    return {"message": "Configuración actualizada"}

@router.post("/logo")
async def upload_school_logo(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.get_current_active_admin)
):
    """Subir el logo institucional"""
    upload_dir = "uploads/branding"
    if not os.path.exists(upload_dir):
        os.makedirs(upload_dir)

    extension = file.filename.split(".")[-1]
    filename = f"school_logo.{extension}" # Nombre fijo para el logo
    file_path = os.path.join(upload_dir, filename)

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    logo_url = f"/uploads/branding/{filename}"
    
    # Guardar la ruta en la tabla de settings
    db_setting = db.query(SystemSetting).filter(SystemSetting.key == "school_logo").first()
    if db_setting:
        db_setting.value = logo_url
    else:
        db.add(SystemSetting(key="school_logo", value=logo_url))
    
    db.commit()
    return {"logo_url": logo_url}