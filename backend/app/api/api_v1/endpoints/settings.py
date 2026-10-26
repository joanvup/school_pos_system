from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.secret_store import encrypt_secret
from app.db.session import get_db
from app.api import deps
from app.models.setting import SystemSetting
from app.models.user import User
from app.utils.images import store_image

router = APIRouter()

PUBLIC_SETTING_KEYS = {
    "school_name",
    "school_logo",
    "currency_symbol",
    "school_support_email",
}

SECRET_SETTING_KEYS = {"smtp_pass"}
MASKED_VALUE = "********"


@router.get("/public")
def get_public_settings(db: Session = Depends(get_db)):
    """Configuración visual sin autenticación. Solo claves de la allowlist."""
    rows = (
        db.query(SystemSetting)
        .filter(SystemSetting.key.in_(PUBLIC_SETTING_KEYS))
        .all()
    )
    return {row.key: row.value for row in rows}


@router.get("/")
def get_all_settings(
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.get_current_active_admin),
):
    """Configuración completa. Solo admin y nunca devuelve secretos."""
    rows = db.query(SystemSetting).all()
    data = {row.key: row.value for row in rows if row.key not in SECRET_SETTING_KEYS}
    data["smtp_pass"] = ""
    data["smtp_pass_set"] = any(
        row.key == "smtp_pass" and bool(row.value) for row in rows
    )
    return data


@router.put("/")
def update_settings(
    payload: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.get_current_active_admin),
):
    for key, value in payload.items():
        if key in SECRET_SETTING_KEYS and (
            value is None or str(value).strip() in ("", MASKED_VALUE)
        ):
            # No se envió una contraseña nueva: conservar la existente.
            continue

        if key in SECRET_SETTING_KEYS:
            value = encrypt_secret(str(value).strip())

        db_setting = db.query(SystemSetting).filter(SystemSetting.key == key).first()
        if db_setting:
            db_setting.value = str(value)
        else:
            db.add(SystemSetting(key=key, value=str(value)))

    db.commit()
    return {"message": "Configuración actualizada"}


@router.post("/logo")
async def upload_school_logo(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.get_current_active_admin),
):
    logo_url = await store_image(
        file,
        subdir="branding",
        prefix="school-logo",
        filename="school_logo.png",
        force_png=True,
        max_side=1024,
        max_bytes=settings.MAX_UPLOAD_BYTES,
    )

    db_setting = (
        db.query(SystemSetting).filter(SystemSetting.key == "school_logo").first()
    )
    if db_setting:
        db_setting.value = logo_url
    else:
        db.add(SystemSetting(key="school_logo", value=logo_url))

    db.commit()
    return {"logo_url": logo_url}
