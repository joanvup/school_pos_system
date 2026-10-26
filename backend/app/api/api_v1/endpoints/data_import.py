import logging
import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.api import deps
from app.core.config import settings
from app.db.session import SessionLocal, get_db
from app.models.ops import ImportJob
from app.utils.excel_handler import (
    process_students_file,
    process_employees_file,
    generate_students_template,
    generate_employees_template
)

router = APIRouter()
logger = logging.getLogger(__name__)

MAX_IMPORT_BYTES = settings.MAX_IMPORT_BYTES
XLSX_MAGIC = b"PK\x03\x04"


async def _read_import_file(file: UploadFile) -> bytes:
    if not file.filename or not file.filename.lower().endswith(".xlsx"):
        raise HTTPException(status_code=400, detail="El archivo debe ser .xlsx")

    contents = await file.read(MAX_IMPORT_BYTES + 1)
    if len(contents) > MAX_IMPORT_BYTES:
        raise HTTPException(status_code=413, detail="El archivo supera el tamaño máximo")
    if not contents:
        raise HTTPException(status_code=400, detail="El archivo está vacío")
    if not contents.startswith(XLSX_MAGIC):
        raise HTTPException(status_code=400, detail="El archivo no es un .xlsx válido")
    return contents


def _create_job(db: Session, user_id: int, kind: str) -> ImportJob:
    job = ImportJob(id=str(uuid.uuid4()), user_id=user_id, kind=kind)
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


@router.get("/template/students")
def download_students_template(
    current_user = Depends(deps.get_current_active_admin)
):
    buf = generate_students_template()
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=plantilla_estudiantes_padres.xlsx"}
    )

@router.get("/template/employees")
def download_employees_template(
    current_user = Depends(deps.get_current_active_admin)
):
    buf = generate_employees_template()
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=plantilla_empleados_staff.xlsx"}
    )

@router.get("/status/{task_id}")
def get_import_status(
    task_id: str,
    db: Session = Depends(get_db),
    current_user = Depends(deps.get_current_active_admin),
):
    # El estado vive en BD: cualquier worker puede responder y solo el
    # creador de la importación puede consultarlo.
    job = (
        db.query(ImportJob)
        .filter(ImportJob.id == task_id, ImportJob.user_id == current_user.id)
        .first()
    )
    if job is None:
        raise HTTPException(status_code=404, detail="Importación no encontrada")
    return {
        "id": job.id,
        "kind": job.kind,
        "progress": job.progress,
        "status": job.status,
        "result": job.result,
        "error": job.error,
        "created_at": job.created_at,
    }

@router.post("/students")
async def import_students_excel(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...), # 'file' debe coincidir con formData.append('file', ...)
    db: Session = Depends(get_db),
    current_user = Depends(deps.get_current_active_admin)
):
    contents = await _read_import_file(file)

    job = _create_job(db, current_user.id, "students")
    background_tasks.add_task(run_async_import, job.id, contents, "students")

    return {"task_id": job.id}

@router.post("/employees")
async def import_employees_excel(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user = Depends(deps.get_current_active_admin)
):
    contents = await _read_import_file(file)

    job = _create_job(db, current_user.id, "employees")
    background_tasks.add_task(run_async_import, job.id, contents, "employees")

    return {"task_id": job.id}

def run_async_import(task_id: str, contents: bytes, import_type: str):
    db = SessionLocal()
    last_progress = -1
    try:
        job = db.get(ImportJob, task_id)
        if job is None:
            return

        def progress_cb(percent: int) -> None:
            nonlocal last_progress
            if percent <= last_progress:
                return
            last_progress = percent
            # El handler confirma la sesión por fila; no hace falta commit aquí.
            job.progress = percent

        if import_type == "students":
            res = process_students_file(contents, db, progress_cb)
        else:
            res = process_employees_file(contents, db, progress_cb)

        job = db.get(ImportJob, task_id)
        job.result = res
        if res.get("error"):
            job.status = "failed"
            job.error = str(res["error"])[:2000]
        else:
            job.progress = 100
            job.status = "completed"
        db.commit()
    except Exception as exc:
        db.rollback()
        logger.exception("Fallo la importación %s", task_id)
        try:
            job = db.get(ImportJob, task_id)
            if job is not None:
                job.status = "failed"
                job.error = str(exc)[:2000]
                db.commit()
        except Exception:
            db.rollback()
            logger.exception("No se pudo registrar el fallo de %s", task_id)
    finally:
        db.close()
